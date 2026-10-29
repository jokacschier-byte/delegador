"""
Motor de distribuicao do SaaS -- carga em dias, com regras de ferias e
rodizio de urgentes, replicando o app local ja validado em producao.
"""

from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone

from .models import Cartorio, Escrevente, Grupo, Natureza, Protocolo


class SemEscreventeDisponivelError(Exception):
    """O grupo da natureza nao tem nenhum escrevente ativo cadastrado."""


def peso_protocolo(natureza: Natureza, matriculas: int, partes: int, grupo: Grupo | None = None) -> float:
    """Peso em dias: base da natureza + ajuste por matricula/parte extra
    (alem da primeira), usando os pesos do grupo informado (ou o grupo
    padrao da natureza, se nenhum for passado)."""
    grupo = grupo or natureza.grupo
    peso = (
        natureza.peso_base_dias
        + grupo.peso_extra_matricula_dias * (max(1, matriculas) - 1)
        + grupo.peso_extra_parte_dias * (max(1, partes) - 1)
    )
    return round(peso, 1)


def carga_atual_dias(cartorio: Cartorio) -> dict[int, float]:
    """{escrevente_id: soma de peso_dias dos protocolos em aberto}.

    So conta protocolos com status ABERTO -- diferente da versao
    anterior (que "esquecia" protocolos depois de 10 dias), aqui a
    carga cai de verdade quando alguem marca o protocolo como
    concluido/diligencia (manualmente no Historico, ou via
    sincronizacao com o SRI).
    """
    totais = (
        Protocolo.objects.filter(
            cartorio=cartorio,
            status=Protocolo.STATUS_ABERTO,
            escrevente_responsavel__isnull=False,
        )
        .values("escrevente_responsavel")
        .annotate(total=Sum("peso_dias"))
    )
    return {linha["escrevente_responsavel"]: round(linha["total"] or 0, 1) for linha in totais}


def contadores_protocolos(cartorio: Cartorio) -> dict[int, dict[str, int]]:
    """{escrevente_id: {"abertos": N, "urgentes": M}} para os protocolos
    em aberto de cada escrevente -- evita uma query por pessoa no painel."""
    linhas = (
        Protocolo.objects.filter(
            cartorio=cartorio, status=Protocolo.STATUS_ABERTO, escrevente_responsavel__isnull=False
        )
        .values("escrevente_responsavel")
        .annotate(abertos=Count("id"), urgentes=Count("id", filter=Q(urgente=True)))
    )
    return {
        linha["escrevente_responsavel"]: {"abertos": linha["abertos"], "urgentes": linha["urgentes"]}
        for linha in linhas
    }


def cor_carga(fracao: float) -> str:
    """Cor (HSL) para uma fracao de carga 0..1 -- verde (folgado) ->
    amarelo -> laranja -> vermelho (no limite)."""
    fracao = max(0.0, min(1.0, fracao))
    matiz = 140 - (140 * fracao)  # 140=verde, ~60=amarelo, ~30=laranja, 0=vermelho
    return f"hsl({matiz:.0f}, 55%, 40%)"


def _add_dias(dia: date, n: int) -> date:
    return dia + timedelta(days=n)


def _entre(dia: date, inicio_incl: date, fim_excl: date) -> bool:
    return inicio_incl <= dia < fim_excl


def ferias_info(escrevente: Escrevente, data_ref: date) -> dict | None:
    """Se `escrevente` estiver sob efeito de algum periodo de ferias na
    `data_ref` (incluindo as janelas de bloqueio antes/depois), retorna
    um dict com periodo/novos_bloqueado/reingresso_bloqueado/em_ferias/
    retorno. Caso contrario, None.

    Regra (igual ao app local): novos protocolos ficam bloqueados de
    (inicio-2 dias) ate (retorno-2 dias); reingressos de diligencia
    ficam bloqueados de (inicio) ate (retorno-1 dia). retorno = fim+1.
    """
    for periodo in escrevente.ferias.all():
        retorno = _add_dias(periodo.fim, 1)
        novos_bloqueado = _entre(data_ref, _add_dias(periodo.inicio, -2), _add_dias(retorno, -2))
        reingresso_bloqueado = _entre(data_ref, periodo.inicio, _add_dias(retorno, -1))
        em_ferias = _entre(data_ref, periodo.inicio, retorno)
        if novos_bloqueado or reingresso_bloqueado or em_ferias:
            return {
                "periodo": periodo,
                "novos_bloqueado": novos_bloqueado,
                "reingresso_bloqueado": reingresso_bloqueado,
                "em_ferias": em_ferias,
                "retorno": retorno,
            }
    return None


def _recebidos_rodada_atual(grupo: Grupo) -> set[int]:
    """IDs dos escreventes (ativos) do grupo que ja receberam um
    protocolo urgente na rodada atual. Quando todo mundo do grupo ja
    recebeu um, a rodada reseta sozinha (volta tudo a valer)."""
    membros_ids = set(grupo.escreventes.filter(ativo=True).values_list("id", flat=True))
    recebidos: set[int] = set()

    urgentes = Protocolo.objects.filter(
        cartorio=grupo.cartorio, urgente=True, natureza__grupo=grupo
    ).order_by("criado_em")

    for protocolo in urgentes:
        if protocolo.escrevente_responsavel_id is None:
            continue
        recebidos.add(protocolo.escrevente_responsavel_id)
        if membros_ids and membros_ids <= recebidos:
            recebidos = set()  # rodada completa: reseta o ciclo

    return recebidos


def escolher_escrevente(protocolo: Protocolo, grupo: Grupo | None = None) -> Escrevente:
    """Escolhe quem deve receber `protocolo`, dentro de `grupo` (ou do
    grupo padrao da natureza, se nao informado):

    1. Parte dos escreventes ativos do grupo.
    2. Tira quem estiver de ferias bloqueado para esse tipo (novo ou
       reingresso) -- a menos que isso esvaziasse o grupo inteiro, caso
       em que a regra de ferias e ignorada (rede de seguranca).
    3. Se o protocolo e urgente, prioriza quem ainda nao recebeu nenhum
       urgente nesta rodada do grupo.
    4. Entre quem sobrou, escolhe quem tem menor carga atual (dias).
    """
    grupo = grupo or protocolo.natureza.grupo
    candidatos = list(grupo.escreventes.filter(ativo=True))
    if not candidatos:
        raise SemEscreventeDisponivelError(
            f"O grupo '{grupo.nome}' não tem nenhum escrevente ativo cadastrado. "
            "Cadastre escreventes nesse grupo antes de distribuir."
        )

    hoje = timezone.localdate()
    disponiveis = []
    for escrevente in candidatos:
        info = ferias_info(escrevente, hoje)
        if info is None:
            disponiveis.append(escrevente)
            continue
        bloqueado = (
            info["reingresso_bloqueado"] if protocolo.tipo == Protocolo.TIPO_REINGRESSO else info["novos_bloqueado"]
        )
        if not bloqueado:
            disponiveis.append(escrevente)
    usar = disponiveis or candidatos

    if protocolo.urgente:
        recebidos = _recebidos_rodada_atual(grupo)
        sem_urgente_na_rodada = [e for e in usar if e.id not in recebidos]
        if sem_urgente_na_rodada and len(sem_urgente_na_rodada) < len(usar):
            usar = sem_urgente_na_rodada

    carga = carga_atual_dias(protocolo.cartorio)
    return min(usar, key=lambda escrevente: carga.get(escrevente.id, 0))


def distribuir(protocolo: Protocolo, grupo: Grupo | None = None) -> Protocolo:
    """Define o escrevente_responsavel do protocolo e salva. Protocolo
    deve ja estar salvo (ter id) e ter peso_dias preenchido."""
    protocolo.escrevente_responsavel = escolher_escrevente(protocolo, grupo=grupo)
    protocolo.save(update_fields=["escrevente_responsavel"])
    return protocolo
