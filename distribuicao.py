"""
Leitura, classificacao e distribuicao de protocolos usando a planilha
local (dados/protocolos.xlsx). Nenhuma funcao aqui toca o SRI -- isso e
responsabilidade de rpa_sri.py, e so entra em jogo depois que a
distribuicao calculada aqui for conferida por uma pessoa.
"""

import pandas as pd

import regras
from configuracao import COLUNAS_PROTOCOLOS, PLANILHA_PROTOCOLOS


def criar_planilha_modelo(caminho=PLANILHA_PROTOCOLOS) -> None:
    """Cria a planilha de protocolos vazia, com as colunas padrao, caso
    ela ainda nao exista."""
    if caminho.exists():
        return

    df = pd.DataFrame(columns=COLUNAS_PROTOCOLOS)
    df.to_excel(caminho, index=False)


def carregar_protocolos(caminho=PLANILHA_PROTOCOLOS) -> pd.DataFrame:
    criar_planilha_modelo(caminho)
    return pd.read_excel(caminho, dtype=str).fillna("")


def salvar_protocolos(df: pd.DataFrame, caminho=PLANILHA_PROTOCOLOS) -> None:
    df.to_excel(caminho, index=False)


def _contexto_da_linha(linha: pd.Series) -> dict | None:
    valor = (linha.get("Inventario (Sim/Nao)", "") or "").strip().lower()
    if valor in ("sim", "s", "true", "1"):
        return {"inventario": True}
    if valor in ("nao", "não", "n", "false", "0"):
        return {"inventario": False}
    return None


def classificar_protocolos(df: pd.DataFrame) -> pd.DataFrame:
    """Preenche Grupo, Tempo Estimado e Observacao a partir da Natureza,
    sem sobrescrever um Grupo ja definido manualmente (override humano)."""
    df = df.copy()

    for indice, linha in df.iterrows():
        if linha.get("Grupo"):
            continue

        classificacao = regras.classificar_natureza(
            linha.get("Natureza", ""), _contexto_da_linha(linha)
        )

        df.at[indice, "Observacao"] = classificacao.observacao

        if classificacao.status != regras.STATUS_OK:
            continue

        df.at[indice, "Grupo"] = classificacao.grupo
        if not linha.get("Tempo Estimado (min)"):
            df.at[indice, "Tempo Estimado (min)"] = str(
                regras.tempo_estimado_minutos(linha.get("Natureza", ""), classificacao.grupo)
            )

    return df


def _minutos(valor) -> int:
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return 0


def relatorio_carga(df: pd.DataFrame) -> dict[str, int]:
    """Retorna {responsavel: minutos totais ja atribuidos}, incluindo com
    0 minutos todo mundo cadastrado em regras.RESPONSAVEIS_POR_GRUPO."""
    carga = {
        nome: 0
        for nomes in regras.RESPONSAVEIS_POR_GRUPO.values()
        for nome in nomes
    }

    for _, linha in df.iterrows():
        responsavel = linha.get("Responsavel", "")
        if responsavel:
            carga[responsavel] = carga.get(responsavel, 0) + _minutos(linha.get("Tempo Estimado (min)"))

    return carga


def distribuir_responsaveis(df: pd.DataFrame) -> pd.DataFrame:
    """Para cada protocolo classificado (Grupo preenchido) sem Responsavel,
    escolhe -- dentro da equipe daquele grupo (regras.RESPONSAVEIS_POR_GRUPO)
    -- quem tem a menor carga atual em minutos, e soma o tempo estimado do
    novo protocolo a carga dessa pessoa antes do proximo sorteio.

    Protocolos sem Grupo (NECESSITA_CONTEXTO ou NAO_CLASSIFICADO) ficam de
    fora: precisam de revisao manual, nao de um responsavel escolhido as
    cegas.
    """
    df = df.copy()
    carga_atual = relatorio_carga(df)

    pendentes = df[(df["Responsavel"] == "") & (df["Grupo"] != "")].index

    for indice in pendentes:
        grupo = df.at[indice, "Grupo"]
        candidatos = regras.RESPONSAVEIS_POR_GRUPO.get(grupo)
        if not candidatos:
            df.at[indice, "Observacao"] = (
                f"Grupo '{grupo}' não tem equipe cadastrada em regras.py."
            )
            continue

        escolhido = min(candidatos, key=lambda nome: carga_atual.get(nome, 0))
        df.at[indice, "Responsavel"] = escolhido
        carga_atual[escolhido] = carga_atual.get(escolhido, 0) + _minutos(
            df.at[indice, "Tempo Estimado (min)"]
        )

    return df
