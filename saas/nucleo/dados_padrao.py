"""
Catalogo padrao de grupos e naturezas, usado para pre-popular um
cartorio-cliente novo -- baseado nas mesmas regras que validamos em
ferramenta_local_rpa/regras.py.

Importante: isso cria Grupo e Natureza, mas NUNCA Escrevente. A equipe
(quem sao as pessoas, quantas sao) e sempre especifica de cada cliente
e deve ser cadastrada por ele mesmo em /admin/nucleo/escrevente/.

Nota sobre "Carta de Adjudicação / Arrematação": no app local essa
natureza dependia de um contexto extra (se estava ligada a inventario)
para decidir entre Simples e Complexo. Aqui, para manter o lançamento
de protocolo simples (só número + natureza + urgente, sem perguntas
extras), ela entra no catálogo como duas naturezas distintas -- quem
lança o protocolo já escolhe a certa.
"""

GRUPO_SIMPLES = "Simples"
GRUPO_NOTIFICACAO_CONSOLIDACAO = "Notificação para Consolidação"
GRUPO_COMPLEXO = "Complexo"
GRUPO_CASOS_ESPECIAIS = "Usucapião e Adjudicação Compulsória"

GRUPOS_PADRAO = [
    GRUPO_SIMPLES,
    GRUPO_NOTIFICACAO_CONSOLIDACAO,
    GRUPO_COMPLEXO,
    GRUPO_CASOS_ESPECIAIS,
]

_TEMPO_PADRAO_POR_GRUPO = {
    GRUPO_SIMPLES: 40,
    GRUPO_NOTIFICACAO_CONSOLIDACAO: 30,
    GRUPO_COMPLEXO: 100,
    GRUPO_CASOS_ESPECIAIS: 150,
}

# Unificação é SEMPRE Simples -- está aqui e só aqui, de propósito.
_NATUREZAS_SIMPLES = [
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
    "Carta de Adjudicação / Arrematação (sem relação com inventário)",
]

_NATUREZAS_NOTIFICACAO_CONSOLIDACAO = [
    "Notificação para Consolidação",
]

# "Unificação" nao entra aqui -- ela e sempre Simples (ver acima).
_NATUREZAS_COMPLEXAS = [
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
    "Carta de Adjudicação / Arrematação (de inventário)",
]

_NATUREZAS_CASOS_ESPECIAIS = [
    "Usucapião Extrajudicial",
    "Procedimento de Adjudicação Compulsória Extrajudicial",
]

# Excecoes ao tempo padrao do grupo (minutos), por nome de natureza.
_TEMPO_ESPECIFICO_POR_NATUREZA = {
    "Contrato Particular de Compra e Venda com/sem Alienação": 35,
    "Retificação de ofício": 90,
    "Formal de Partilha - Inventário": 120,
}


def _montar_catalogo() -> list[tuple[str, str, int]]:
    catalogo = []
    for nomes, grupo in [
        (_NATUREZAS_SIMPLES, GRUPO_SIMPLES),
        (_NATUREZAS_NOTIFICACAO_CONSOLIDACAO, GRUPO_NOTIFICACAO_CONSOLIDACAO),
        (_NATUREZAS_COMPLEXAS, GRUPO_COMPLEXO),
        (_NATUREZAS_CASOS_ESPECIAIS, GRUPO_CASOS_ESPECIAIS),
    ]:
        for nome in nomes:
            minutos = _TEMPO_ESPECIFICO_POR_NATUREZA.get(nome, _TEMPO_PADRAO_POR_GRUPO[grupo])
            catalogo.append((nome, grupo, minutos))
    return catalogo


NATUREZAS_PADRAO = _montar_catalogo()


def carregar_catalogo_padrao(cartorio) -> tuple[int, int]:
    """Cria (sem duplicar) os Grupos e Naturezas padrao para `cartorio`.

    Nao cria nenhum Escrevente -- isso fica por conta de cada cliente.
    Retorna (grupos_criados, naturezas_criadas).
    """
    from .models import Grupo, Natureza

    grupos_por_nome = {}
    grupos_criados = 0
    for nome_grupo in GRUPOS_PADRAO:
        grupo, criado = Grupo.objects.get_or_create(cartorio=cartorio, nome=nome_grupo)
        grupos_por_nome[nome_grupo] = grupo
        grupos_criados += int(criado)

    naturezas_criadas = 0
    for nome_natureza, nome_grupo, minutos in NATUREZAS_PADRAO:
        _, criado = Natureza.objects.get_or_create(
            cartorio=cartorio,
            nome=nome_natureza,
            defaults={"grupo": grupos_por_nome[nome_grupo], "tempo_estimado_minutos": minutos},
        )
        naturezas_criadas += int(criado)

    return grupos_criados, naturezas_criadas
