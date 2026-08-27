"""
Regras de classificacao de protocolos por natureza.

Fase inicial: 100% baseada em regras programadas (sem IA), para que a
logica seja testavel e previsivel. Nenhum dado sai deste computador.

Quando a natureza nao estiver no dicionario, o protocolo cai em
"NAO_CLASSIFICADO" e deve ser revisado manualmente -- o robo nunca deve
adivinhar um destino para um caso ambiguo.
"""

NAO_CLASSIFICADO = "NAO_CLASSIFICADO"

# natureza (como aparece no SRI) -> complexidade / grupo responsavel.
# grupo=None significa que a distribuicao.py deve decidir o responsavel
# pela carga de trabalho, em vez de um grupo fixo.
REGRAS_NATUREZA = {
    "Unificação": {"complexidade": "SIMPLES", "grupo": None},
    "Formal de Partilha - Inventário": {"complexidade": "COMPLEXO", "grupo": None},
    "Usucapião Extrajudicial": {"complexidade": "ESPECIAL", "grupo": "MARCELO"},
    "Notificação para Consolidação": {"complexidade": "ESPECIAL", "grupo": "ADRIANA/ADRIELI"},
}


def classificar_natureza(natureza: str) -> dict:
    """Retorna {'complexidade': ..., 'grupo': ...} para a natureza informada.

    Faz correspondencia exata (apos strip). Nao tenta interpretar texto
    livre ou variacoes -- isso fica para uma etapa futura, se necessario.
    """
    if not natureza:
        return {"complexidade": NAO_CLASSIFICADO, "grupo": None}

    regra = REGRAS_NATUREZA.get(natureza.strip())
    if regra is None:
        return {"complexidade": NAO_CLASSIFICADO, "grupo": None}

    return dict(regra)
