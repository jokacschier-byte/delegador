"""
Ponto de entrada do DistribuidorSRI.

Uso:
    py main.py listar-janelas     -> Fase 1: lista as janelas abertas no Windows
    py main.py localizar-sri      -> Fase 2: tenta localizar a janela do SRI
    py main.py classificar        -> le dados/protocolos.xlsx e classifica por natureza
    py main.py distribuir NOME1 NOME2 ... -> classifica e distribui entre os responsaveis

Nenhum desses comandos clica ou salva nada no SRI.
"""

import sys

import distribuicao
import rpa_sri


def cmd_listar_janelas() -> None:
    titulos = rpa_sri.listar_janelas()
    print("Janelas abertas:")
    print("-" * 50)
    for titulo in titulos:
        print(titulo)


def cmd_localizar_sri() -> None:
    janela = rpa_sri.localizar_janela_sri()
    if janela is None:
        print("Janela do SRI não encontrada.")
        return
    print(f"Janela do SRI encontrada: {janela.window_text()!r}")


def cmd_classificar() -> None:
    df = distribuicao.carregar_protocolos()
    df = distribuicao.classificar_protocolos(df)
    distribuicao.salvar_protocolos(df)
    print(f"{len(df)} protocolo(s) classificado(s) em {distribuicao.PLANILHA_PROTOCOLOS}")


def cmd_distribuir(responsaveis: list[str]) -> None:
    df = distribuicao.carregar_protocolos()
    df = distribuicao.classificar_protocolos(df)
    df = distribuicao.distribuir_responsaveis(df, responsaveis)
    distribuicao.salvar_protocolos(df)
    print(f"{len(df)} protocolo(s) processado(s) em {distribuicao.PLANILHA_PROTOCOLOS}")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return

    comando, *args = sys.argv[1:]

    if comando == "listar-janelas":
        cmd_listar_janelas()
    elif comando == "localizar-sri":
        cmd_localizar_sri()
    elif comando == "classificar":
        cmd_classificar()
    elif comando == "distribuir":
        cmd_distribuir(args)
    else:
        print(f"Comando desconhecido: {comando}\n")
        print(__doc__)


if __name__ == "__main__":
    main()
