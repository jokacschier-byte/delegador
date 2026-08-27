"""
Ponto de entrada do DistribuidorSRI.

Uso:
    py main.py listar-janelas   -> Fase 1: lista as janelas abertas no Windows
    py main.py localizar-sri    -> Fase 2: tenta localizar a janela do SRI
    py main.py classificar      -> le dados/protocolos.xlsx e classifica por natureza
    py main.py distribuir       -> classifica e distribui entre os responsaveis (regras.py)
    py main.py carga            -> mostra a carga atual (em horas) de cada responsavel

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


def cmd_distribuir() -> None:
    df = distribuicao.carregar_protocolos()
    df = distribuicao.classificar_protocolos(df)
    df = distribuicao.distribuir_responsaveis(df)
    distribuicao.salvar_protocolos(df)
    print(f"{len(df)} protocolo(s) processado(s) em {distribuicao.PLANILHA_PROTOCOLOS}")


def cmd_carga() -> None:
    df = distribuicao.carregar_protocolos()
    carga = distribuicao.relatorio_carga(df)
    for nome, minutos in sorted(carga.items(), key=lambda item: -item[1]):
        horas, resto = divmod(minutos, 60)
        print(f"{nome:20s} {horas:2d}h{resto:02d}  ({minutos} min)")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return

    comando = sys.argv[1]

    if comando == "listar-janelas":
        cmd_listar_janelas()
    elif comando == "localizar-sri":
        cmd_localizar_sri()
    elif comando == "classificar":
        cmd_classificar()
    elif comando == "distribuir":
        cmd_distribuir()
    elif comando == "carga":
        cmd_carga()
    else:
        print(f"Comando desconhecido: {comando}\n")
        print(__doc__)


if __name__ == "__main__":
    main()
