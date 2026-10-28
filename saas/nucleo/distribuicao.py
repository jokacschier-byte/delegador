"""
Motor de distribuicao do SaaS.

Mesma ideia da ferramenta_local_rpa/distribuicao.py: escolher, dentro do
grupo competente para a natureza do protocolo, quem tem a menor carga
atual (em minutos estimados) -- so que aqui o grupo/equipe vem do banco
de dados, configurado pelo proprio cartorio-cliente, em vez de fixo no
codigo.
"""

from django.db.models import Sum

from .models import Cartorio, Escrevente, Protocolo


class SemEscreventeDisponivelError(Exception):
    """O grupo da natureza nao tem nenhum escrevente ativo cadastrado."""


def carga_atual_minutos(cartorio: Cartorio) -> dict[int, int]:
    """Retorna {escrevente_id: minutos totais ja atribuidos a ele}."""
    totais = (
        Protocolo.objects.filter(cartorio=cartorio, escrevente_responsavel__isnull=False)
        .values("escrevente_responsavel")
        .annotate(total=Sum("tempo_estimado_minutos"))
    )
    return {linha["escrevente_responsavel"]: linha["total"] or 0 for linha in totais}


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
