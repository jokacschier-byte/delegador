"""
Regras de competencia e classificacao do cartorio.

Isto e a fonte da verdade sobre "quem pode analisar o que". A IA/robo
nunca decide isso sozinha -- este arquivo e so a transcricao das regras
internas reais, e distribuicao.py so pode escolher um responsavel dentro
do grupo que este arquivo determinar.

Filosofia de casamento de natureza:
    A comparacao e SEMPRE por texto exato (normalizado), nunca por
    substring/palavra-chave solta. Isso e proposital: "retificação" ou
    "imissão de posse" sozinhos NÃO decidem nada, porque o cartório tem
    mais de um tipo de retificação e de imissão de posse, cada um com um
    grupo diferente. O texto da "Natureza Formal do Título" que vem do
    SRI já costuma trazer o qualificador (ex.: "Retificação de Ofício"
    vs. "Retificação Administrativa / Inserção"), então o casamento exato
    já resolve a maior parte dos casos sem ambiguidade.
    A única natureza que o SRI não descreve de forma auto-suficiente é
    "Carta de Adjudicação / Arrematação": o mesmo texto pode ser simples
    ou complexo dependendo de estar ligado a um inventário ou não. Para
    essa, classificar_natureza() exige um `contexto` explícito.
"""

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Grupos e equipe responsavel por cada um (secao 4 do prompt mestre)
# ---------------------------------------------------------------------------

GRUPO_SIMPLES = "SIMPLES"
GRUPO_NOTIFICACAO_CONSOLIDACAO = "NOTIFICACAO_CONSOLIDACAO"
GRUPO_COMPLEXO = "COMPLEXO"
GRUPO_MARCELO = "MARCELO"

RESPONSAVEIS_POR_GRUPO = {
    GRUPO_SIMPLES: ["Priscila", "Francis", "Elaine"],
    # "Adriana/Adrieli" e uma unica funcao/equipe, nao duas pessoas para
    # fazer rodizio -- entao a lista tem um unico item.
    GRUPO_NOTIFICACAO_CONSOLIDACAO: ["Adriana/Adrieli"],
    GRUPO_COMPLEXO: ["Jana", "Pamela"],
    GRUPO_MARCELO: ["Marcelo"],
}

# ---------------------------------------------------------------------------
# Status possiveis de uma classificacao
# ---------------------------------------------------------------------------

STATUS_OK = "OK"
STATUS_NECESSITA_CONTEXTO = "NECESSITA_CONTEXTO"
STATUS_NAO_CLASSIFICADO = "NAO_CLASSIFICADO"


@dataclass
class Classificacao:
    natureza: str
    grupo: str | None
    status: str
    observacao: str = ""


def _normalizar(texto: str) -> str:
    return (texto or "").strip().lower()


# ---------------------------------------------------------------------------
# Secao 5 do prompt mestre -- Priscila / Francis / Elaine (SIMPLES)
# Unificacao esta aqui e SOMENTE aqui: "Unificação é SEMPRE SIMPLES".
# ---------------------------------------------------------------------------

_NATUREZAS_SIMPLES_TEXTO = [
    "Abertura de Matrícula",
    "Aditivos Cedulares",
    "Alteração de Razão Social",
    "Alteração denominação do imóvel",
    "Atualização de confrontantes",
    "Averbação de Divórcio",
    "Averbação de erro",
    "Baixa de Alienação",
    "Baixa Nota Promissória",
    "Cancelamento de Garantias e Registros",
    "Casamentos/Pacto",
    "Cédulas (alienação fiduciária, hipoteca, penhor)",
    "Cessão de direitos ou crédito",
    "Consolidação de Propriedade",
    "Construção / Ampliação / Edificação / Demolição",
    "Contrato de Abertura de Teto",
    "Contrato de Locação / Contrato Arrendamento",
    "Contrato Particular de Compra e Venda com/sem Alienação",
    "CV Cohapar",
    "Contrato Particular/Escritura Pública somente Alienação Fiduciária",
    "Confissão de dívida",
    "Dados imóvel",
    "Dados pessoas",
    "Desmembramento",
    "Unificação",
    "Formal de partilha — Divórcio",
    "Doação",
    "Escritura Pública de Compra e Venda",
    "Escritura Pública ou Mandado de Servidão",
    "Escrituras de Hipoteca / Abertura de crédito",
    "Existência de Ação / Averbação Premonitória",
    "Indisponibilidade / Cancelamento",
    "Integralização de capital social",
    "Instituição de Usufruto",
    "Levantamento de Penhora",
    "Mandado Imissão de Posse (Servidão)",
    "Pacto L3",
    "Penhora / Arresto",
    "Permuta",
    "Quitação",
    "Registro de Sentença / Hipoteca Judiciária",
    "Renúncia e Extinção de Usufruto",
    "Retificação de ofício",
    "Requerimento para Averbação de Existência de Ação",
    "Somente averbação de Georreferenciamento",
    "T.A.C.",
    "Termo de Ajustamento de Conduta",
    "Compensação de reserva legal",
    "Averbação de patrimônio de afetação com abertura de matrícula das unidades projetadas",
    "Desafetação de patrimônio de empresa",
    "Leilões negativos",
    "Transferência de matrícula",
]
NATUREZAS_SIMPLES = frozenset(_normalizar(n) for n in _NATUREZAS_SIMPLES_TEXTO)

# ---------------------------------------------------------------------------
# Secao 6 -- Notificacao para consolidacao (Adriana/Adrieli).
# Cuidado: "Consolidação de Propriedade" (acima) NÃO é o mesmo protocolo.
# ---------------------------------------------------------------------------

NATUREZAS_NOTIFICACAO_CONSOLIDACAO = frozenset(
    _normalizar(n) for n in ["Notificação para Consolidação"]
)

# ---------------------------------------------------------------------------
# Secao 7 -- Jana/Pamela (COMPLEXO). "Unificação" foi removida daqui de
# proposito: a secao 7 do prompt mestre corrige a lista original dizendo
# que Unificação é sempre SIMPLES.
# ---------------------------------------------------------------------------

_NATUREZAS_COMPLEXAS_TEXTO = [
    "Cessão de Direitos Hereditários",
    "Condomínio",
    "Divisão Amigável",
    "Escritura ou mandado de Desapropriação",
    "Escritura Pública de Inventário",
    "Estremação",
    "Formal de Partilha - Inventário",
    "Incorporação de Empresas",
    "Incorporação de bens / Cisão",
    "Mandado Imissão de Posse (Desapropriação)",
    "Registro de Sentença Usucapião Judicial",
    "Regularização Fundiária — Programa Moradia Legal",
    "Retificação Adm. / Inserção",
    "Retificação de Condomínio",
]
NATUREZAS_COMPLEXAS = frozenset(_normalizar(n) for n in _NATUREZAS_COMPLEXAS_TEXTO)

# ---------------------------------------------------------------------------
# Secao 8 -- Marcelo (casos especificos)
# ---------------------------------------------------------------------------

NATUREZAS_MARCELO = frozenset(
    _normalizar(n)
    for n in [
        "Usucapião Extrajudicial",
        "Procedimento de Adjudicação Compulsória Extrajudicial",
    ]
)

# ---------------------------------------------------------------------------
# Secao 9 -- Carta de Adjudicação / Arrematação: única natureza que
# depende de contexto externo (se está ligada a inventário ou não).
# ---------------------------------------------------------------------------

NATUREZAS_CONTEXTO_INVENTARIO = frozenset(
    _normalizar(n)
    for n in ["Carta de Adjudicação", "Carta de Arrematação", "Carta de Adjudicação / Arrematação"]
)

# ---------------------------------------------------------------------------
# Secao 16 -- estimativas iniciais de tempo (minutos), usadas ate termos
# historico real do SRI para aprender por natureza/pessoa. São palpites
# de partida, não valores medidos -- ajustar livremente.
# ---------------------------------------------------------------------------

TEMPO_ESTIMADO_PADRAO_MINUTOS = {
    GRUPO_SIMPLES: 40,
    GRUPO_NOTIFICACAO_CONSOLIDACAO: 30,
    GRUPO_COMPLEXO: 100,
    GRUPO_MARCELO: 150,
}

TEMPOS_ESTIMADOS_POR_NATUREZA_MINUTOS = {
    _normalizar("Contrato Particular de Compra e Venda com/sem Alienação"): 35,
    _normalizar("Retificação de ofício"): 90,
    _normalizar("Formal de Partilha - Inventário"): 120,
}


def tempo_estimado_minutos(natureza: str, grupo: str | None) -> int:
    especifico = TEMPOS_ESTIMADOS_POR_NATUREZA_MINUTOS.get(_normalizar(natureza))
    if especifico is not None:
        return especifico
    return TEMPO_ESTIMADO_PADRAO_MINUTOS.get(grupo, 60)


# ---------------------------------------------------------------------------
# Classificacao
# ---------------------------------------------------------------------------


def classificar_natureza(natureza: str, contexto: dict | None = None) -> Classificacao:
    """Classifica uma natureza de protocolo no grupo responsavel.

    `contexto` só é usado (e só é necessário) para "Carta de Adjudicação /
    Arrematação": passe {"inventario": True} ou {"inventario": False}.
    Para qualquer outra natureza, `contexto` é ignorado.
    """
    normalizado = _normalizar(natureza)

    if not normalizado:
        return Classificacao(natureza, None, STATUS_NAO_CLASSIFICADO, "Natureza vazia.")

    if normalizado in NATUREZAS_CONTEXTO_INVENTARIO:
        eh_inventario = (contexto or {}).get("inventario")
        if eh_inventario is None:
            return Classificacao(
                natureza,
                None,
                STATUS_NECESSITA_CONTEXTO,
                "Carta de Adjudicação/Arrematação: é preciso informar se está "
                "ligada a um inventário (contexto={'inventario': True/False}) "
                "antes de decidir entre SIMPLES e COMPLEXO.",
            )
        grupo = GRUPO_COMPLEXO if eh_inventario else GRUPO_SIMPLES
        return Classificacao(natureza, grupo, STATUS_OK)

    if normalizado in NATUREZAS_NOTIFICACAO_CONSOLIDACAO:
        return Classificacao(natureza, GRUPO_NOTIFICACAO_CONSOLIDACAO, STATUS_OK)

    if normalizado in NATUREZAS_MARCELO:
        return Classificacao(natureza, GRUPO_MARCELO, STATUS_OK)

    if normalizado in NATUREZAS_SIMPLES:
        return Classificacao(natureza, GRUPO_SIMPLES, STATUS_OK)

    if normalizado in NATUREZAS_COMPLEXAS:
        return Classificacao(natureza, GRUPO_COMPLEXO, STATUS_OK)

    return Classificacao(
        natureza,
        None,
        STATUS_NAO_CLASSIFICADO,
        "Natureza não mapeada nas regras do cartório -- precisa revisão manual.",
    )
