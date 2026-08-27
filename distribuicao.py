"""
Leitura, classificacao e distribuicao de protocolos usando a planilha
local (dados/protocolos.xlsx). Nenhuma funcao aqui toca o SRI -- isso e
responsabilidade de rpa_sri.py, e so entra em jogo depois que a
distribuicao calculada aqui for conferida por uma pessoa.
"""

import pandas as pd

from configuracao import COLUNAS_PROTOCOLOS, PLANILHA_PROTOCOLOS
from regras import NAO_CLASSIFICADO, classificar_natureza


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


def classificar_protocolos(df: pd.DataFrame) -> pd.DataFrame:
    """Preenche Complexidade e Grupo a partir da Natureza, sem sobrescrever
    valores ja definidos manualmente."""
    df = df.copy()

    for indice, linha in df.iterrows():
        if linha.get("Complexidade"):
            continue

        classificacao = classificar_natureza(linha.get("Natureza", ""))
        df.at[indice, "Complexidade"] = classificacao["complexidade"]
        if classificacao["grupo"]:
            df.at[indice, "Grupo"] = classificacao["grupo"]

    return df


def distribuir_responsaveis(df: pd.DataFrame, responsaveis: list[str]) -> pd.DataFrame:
    """Distribui, por rodizio equilibrado pela carga atual, os protocolos
    que ainda nao tem Responsavel nem Grupo fixo definido.

    Protocolos com Grupo preenchido (ex.: "MARCELO") nao entram no
    rodizio -- ja tem destino certo pela regra de natureza. Protocolos
    com natureza nao mapeada (NAO_CLASSIFICADO) tambem ficam de fora:
    precisam de revisao manual antes de ganhar um responsavel, em vez de
    seguir para uma pessoa aleatoria por falta de regra.
    """
    if not responsaveis:
        raise ValueError("Lista de responsaveis nao pode ser vazia.")

    df = df.copy()

    carga_atual = {
        responsavel: (df["Responsavel"] == responsavel).sum()
        for responsavel in responsaveis
    }

    pendentes = df[
        (df["Responsavel"] == "")
        & (df["Grupo"] == "")
        & (df["Complexidade"] != NAO_CLASSIFICADO)
    ].index

    for indice in pendentes:
        responsavel_escolhido = min(carga_atual, key=carga_atual.get)
        df.at[indice, "Responsavel"] = responsavel_escolhido
        carga_atual[responsavel_escolhido] += 1

    return df
