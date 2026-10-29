"""
Catalogo padrao de grupos e naturezas, usado para pre-popular um
cartorio-cliente novo -- agora baseado no catalogo real validado no
app local em producao (ferias, pesos por matricula/parte, naturezas
completas), nao mais na primeira versao simplificada.

Importante: isso cria Grupo e Natureza, mas NUNCA Escrevente. A equipe
(quem sao as pessoas, quantas sao) e sempre especifica de cada cliente
e deve ser cadastrada por ele mesmo em /admin/nucleo/escrevente/.

Sobre "Carta de Adjudicação" e "Carta de Arrematação": sao SIMPLES por
padrao, mas tem `grupo_se_inventario` apontando para COMPLEXO -- o
formulario "Lançar protocolo" mostra "É inventário?" so para essas
naturezas, e troca o grupo efetivo quando marcado.
"""

GRUPO_SIMPLES = "Simples"
GRUPO_COMPLEXO = "Complexo"
GRUPO_CONSOLIDACAO = "Consolidação/Notificação"
GRUPO_ESPECIAL = "Especial"

# nome do grupo -> peso extra (em dias) por matricula/parte alem da
# primeira. Valores calibrados no app local ja em uso.
GRUPOS_PADRAO = {
    GRUPO_SIMPLES: {"peso_extra_matricula_dias": 0.5, "peso_extra_parte_dias": 0.2},
    GRUPO_COMPLEXO: {"peso_extra_matricula_dias": 1.0, "peso_extra_parte_dias": 0.4},
    GRUPO_CONSOLIDACAO: {"peso_extra_matricula_dias": 0.3, "peso_extra_parte_dias": 0.1},
    GRUPO_ESPECIAL: {"peso_extra_matricula_dias": 1.5, "peso_extra_parte_dias": 0.5},
}

# (nome, grupo, peso_base_dias, grupo_se_inventario)
NATUREZAS_PADRAO = [
    # Simples
    ("Aditivo cedular", GRUPO_SIMPLES, 3, None),
    ("Alienação Fiduciária", GRUPO_SIMPLES, 3, None),
    ("Auto de Penhora", GRUPO_SIMPLES, 3, None),
    ("Cancelamento de Alienação Fiduciária Consórcio", GRUPO_SIMPLES, 3, None),
    ("Cancelamento de Arrolamento", GRUPO_SIMPLES, 3, None),
    ("Cancelamento de Averbação Premonitória", GRUPO_SIMPLES, 3, None),
    ("Cancelamento de Existência de Ação", GRUPO_SIMPLES, 3, None),
    ("Cancelamento de Garantias (Hipoteca/AF/Penhor)", GRUPO_SIMPLES, 3, None),
    ("Cancelamento de Indisponibilidade", GRUPO_SIMPLES, 3, None),
    ("Cancelamento de Penhora", GRUPO_SIMPLES, 3, None),
    ("Carta de Adjudicação", GRUPO_SIMPLES, 3, GRUPO_COMPLEXO),
    ("Carta de Arrematação", GRUPO_SIMPLES, 3, GRUPO_COMPLEXO),
    ("Consolidação da Propriedade Fiduciária", GRUPO_SIMPLES, 3, None),
    ("Contrato Particular de Promessa de Compra e Venda", GRUPO_SIMPLES, 3, None),
    ("Contrato de Abertura de Crédito Rural Fixo", GRUPO_SIMPLES, 3, None),
    ("Contrato de Abertura de Teto", GRUPO_SIMPLES, 3, None),
    ("Cédula Rural Hipotecária", GRUPO_SIMPLES, 3, None),
    ("Cédula Rural Pignoratícia", GRUPO_SIMPLES, 3, None),
    ("Cédula Rural Pignoratícia e Hipotecária", GRUPO_SIMPLES, 3, None),
    ("Cédula de Crédito Bancário", GRUPO_SIMPLES, 3, None),
    ("Cédula de Produto Rural", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Compra e Venda Com Cláusulas Especiais", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Compra e Venda Sem Cláusulas Especiais", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Confissão de Dívida com Alienação Fiduciária", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Dação em Pagamento", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Divórcio", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Doação", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Doação com Usufruto", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Instituição de Servidão", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Instituição de Usufruto", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Pacto Antenupcial - Registro L3", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Permuta", GRUPO_SIMPLES, 3, None),
    ("Escritura Pública de Renúncia de Usufruto", GRUPO_SIMPLES, 3, None),
    ("Formal de Partilha - Dissolução União Estável", GRUPO_SIMPLES, 3, None),
    ("Formal de Partilha - Divórcio", GRUPO_SIMPLES, 3, None),
    ("Instrumento Particular de Alienação Fiduciária", GRUPO_SIMPLES, 3, None),
    ("Instrumento Particular de Alienação Fiduciária com Recursos de Consórcio", GRUPO_SIMPLES, 3, None),
    ("Instrumento Particular de Compra e Venda", GRUPO_SIMPLES, 3, None),
    ("Instrumento Particular de Compra e Venda - COHAPAR", GRUPO_SIMPLES, 3, None),
    ("Instrumento Particular de Compra e Venda com AF e Recursos de Consórcio", GRUPO_SIMPLES, 3, None),
    ("Instrumento Particular de Compra e Venda com Alienação Fiduciária", GRUPO_SIMPLES, 3, None),
    ("Instrumento Particular de Compra e Venda com Hipoteca", GRUPO_SIMPLES, 3, None),
    ("Instrumento Particular de Compromisso de Compra e Venda com Hipoteca", GRUPO_SIMPLES, 3, None),
    ("Integralização de Capital Social", GRUPO_SIMPLES, 3, None),
    ("Mandado de Servidão", GRUPO_SIMPLES, 3, None),
    ("Ordem de Indisponibilidade ou Bloqueio de Matrícula", GRUPO_SIMPLES, 3, None),
    ("Quitação COHAPAR", GRUPO_SIMPLES, 3, None),
    ("Registro de Sentença / Hipoteca Judiciária", GRUPO_SIMPLES, 3, None),
    ("Requerimento", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Abertura de Matrícula", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Alteração de Perímetro", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Alteração de Razão Social", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Averbação Premonitória", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Averbação de Casamento", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Averbação de Existência de Ação", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Averbação de Leilão Negativo", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Averbação de Óbito", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Cancelamento de Arrendamento", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Cancelamento de Cláusula Resolutiva/Restritiva", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Construção", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Demolição", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Desmembramento", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Extinção de Usufruto por Morte", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Qualificação Objetiva de Imóvel Urbano", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Qualificação Subjetiva / Alteração Dados Pessoais", GRUPO_SIMPLES, 3, None),
    ("Requerimento para Unificação", GRUPO_SIMPLES, 3, None),
    ("Retificação de ofício (art. 213, I LRP)", GRUPO_SIMPLES, 3, None),
    ("Só Averbação de Georreferenciamento", GRUPO_SIMPLES, 3, None),
    ("Termo de Ajustamento de Conduta", GRUPO_SIMPLES, 3, None),

    # Complexo
    ("Cessão de Direitos Hereditários", GRUPO_COMPLEXO, 6, None),
    ("Escritura Pública de Desapropriação", GRUPO_COMPLEXO, 6, None),
    ("Escritura Pública de Divisão Amigável", GRUPO_COMPLEXO, 6, None),
    ("Escritura Pública de Estremação", GRUPO_COMPLEXO, 6, None),
    ("Escritura Pública de Inventário e Partilha", GRUPO_COMPLEXO, 6, None),
    ("Formal de Partilha - Inventário", GRUPO_COMPLEXO, 6, None),
    ("Incorporação de Condomínio", GRUPO_COMPLEXO, 6, None),
    ("Instituição de Condomínio", GRUPO_COMPLEXO, 6, None),
    ("Instrumento de Cisão de Empresa", GRUPO_COMPLEXO, 6, None),
    ("Instrumento de Incorporação de Empresas", GRUPO_COMPLEXO, 6, None),
    ("Mandado de Desapropriação", GRUPO_COMPLEXO, 6, None),
    ("Mandado de Usucapião Judicial", GRUPO_COMPLEXO, 6, None),
    ("Procedimento de Retificação Administrativa Registral", GRUPO_COMPLEXO, 6, None),
    ("Regularização Fundiária - Programa Moradia Legal", GRUPO_COMPLEXO, 6, None),
    ("Retificação de Condomínio", GRUPO_COMPLEXO, 6, None),

    # Consolidação/Notificação
    ("Requerimento para Notificação de Devedor Fiduciante", GRUPO_CONSOLIDACAO, 2, None),

    # Especial
    ("Procedimento de Adjudicação Compulsória Extrajudicial", GRUPO_ESPECIAL, 10, None),
    ("Procedimento de Usucapião Extrajudicial", GRUPO_ESPECIAL, 10, None),
]


def carregar_catalogo_padrao(cartorio) -> tuple[int, int]:
    """Cria (sem duplicar) os Grupos e Naturezas padrao para `cartorio`.

    Nao cria nenhum Escrevente -- isso fica por conta de cada cliente.
    Retorna (grupos_criados, naturezas_criadas).
    """
    from .models import Grupo, Natureza

    grupos_por_nome = {}
    grupos_criados = 0
    for nome_grupo, pesos in GRUPOS_PADRAO.items():
        grupo, criado = Grupo.objects.get_or_create(
            cartorio=cartorio,
            nome=nome_grupo,
            defaults={
                "peso_extra_matricula_dias": pesos["peso_extra_matricula_dias"],
                "peso_extra_parte_dias": pesos["peso_extra_parte_dias"],
            },
        )
        grupos_por_nome[nome_grupo] = grupo
        grupos_criados += int(criado)

    naturezas_criadas = 0
    for nome_natureza, nome_grupo, peso_dias, nome_grupo_inventario in NATUREZAS_PADRAO:
        _, criado = Natureza.objects.get_or_create(
            cartorio=cartorio,
            nome=nome_natureza,
            defaults={
                "grupo": grupos_por_nome[nome_grupo],
                "peso_base_dias": peso_dias,
                "grupo_se_inventario": grupos_por_nome[nome_grupo_inventario] if nome_grupo_inventario else None,
            },
        )
        naturezas_criadas += int(criado)

    return grupos_criados, naturezas_criadas
