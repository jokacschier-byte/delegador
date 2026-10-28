"""
Motor de distribuicao do SaaS.

Mesma ideia da ferramenta_local_rpa/distribuicao.py: escolher, dentro do
grupo competente para a natureza do protocolo, quem tem a menor carga
atual (em minutos estimados) -- so que aqui o grupo/equipe vem do banco
de dados, configurado pelo proprio cartorio-cliente, em vez de fixo no
codigo.
"""

from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from .models import Cartorio, Escrevente, Protocolo


class SemEscreventeDisponivelError(Exception):
    """O grupo da natureza nao tem nenhum escrevente ativo cadastrado."""


# Depois desses dias, um protocolo para de contar na carga de quem o
# recebeu -- presume-se que ja foi entregue, mesmo que ninguem tenha
# marcado o Status como "Concluido" manualmente. Isso e so uma hipotese
# de trabalho (nao apagamos nada, nem mudamos o Status do protocolo):
# ela so limita a janela de tempo que entra na conta da carga atual,
# tanto para o que aparece no painel quanto para a escolha de quem
# recebe o proximo protocolo.
JANELA_CARGA_DIAS = 10

# Carga (em minutos) considerada "equipe cheia" para fins de cor/barra
# no painel -- 40h de trabalho dentro da janela de 10 dias. E um palpite
# inicial, ajustavel; nao limita quantos protocolos alguem pode receber.
CAPACIDADE_REFERENCIA_MINUTOS = 2400


def carga_atual_minutos(cartorio: Cartorio) -> dict[int, int]:
    """Retorna {escrevente_id: minutos somados dos protocolos atribuidos
    a ele nos ultimos JANELA_CARGA_DIAS dias}.

    Nao precisa de nenhuma tarefa agendada para "zerar" a carga depois de
    10 dias -- o filtro por data e recalculado a cada chamada, entao um
    protocolo simplesmente para de contar sozinho assim que fica mais
    velho que a janela.
    """
    limite = timezone.now() - timedelta(days=JANELA_CARGA_DIAS)

    totais = (
        Protocolo.objects.filter(
            cartorio=cartorio,
            escrevente_responsavel__isnull=False,
            criado_em__gte=limite,
        )
        .values("escrevente_responsavel")
        .annotate(total=Sum("tempo_estimado_minutos"))
    )
    return {linha["escrevente_responsavel"]: linha["total"] or 0 for linha in totais}


def cor_carga(minutos: int, capacidade=CAPACIDADE_REFERENCIA_MINUTOS) -> str:
    """Cor (HSL) para representar a carga: verde (folgado) -> amarelo ->
    laranja -> vermelho (no limite da capacidade de referencia ou alem).
    """
    fracao = max(0.0, min(1.0, minutos / capacidade)) if capacidade else 0.0
    matiz = 140 - (140 * fracao)  # 140=verde, ~60=amarelo, ~30=laranja, 0=vermelho
    return f"hsl({matiz:.0f}, 55%, 40%)"


def escolher_escrevente(protocolo: Protocolo) -> Escrevente:
    """Escolhe, entre os escreventes ativos do grupo da natureza do
    protocolo, aquele com menor carga atual."""
    candidatos = list(protocolo.natureza.grupo.escreventes.filter(ativo=True))
    if not candidatos:
        raise SemEscreventeDisponivelError(
            f"O grupo '{protocolo.natureza.grupo.nome}' não tem nenhum escrevente "
            "ativo cadastrado. Cadastre escreventes nesse grupo antes de distribuir."
        )

    carga = carga_atual_minutos(protocolo.cartorio)
    return min(candidatos, key=lambda escrevente: carga.get(escrevente.id, 0))


def distribuir(protocolo: Protocolo) -> Protocolo:
    """Define o escrevente_responsavel do protocolo e salva. Protocolo
    deve ja estar salvo (ter id) e ter tempo_estimado_minutos preenchido."""
    protocolo.escrevente_responsavel = escolher_escrevente(protocolo)
    protocolo.save(update_fields=["escrevente_responsavel"])
    return protocolo
