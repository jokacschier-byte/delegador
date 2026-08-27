"""
Camada de automacao (RPA) do SRI.

Regra de ouro: enquanto uma fase nao tiver sido validada manualmente,
a funcao correspondente nao deve existir de verdade aqui -- so um stub
que avisa o que falta. Isso evita que um erro de automacao distribua
protocolos para a pessoa errada ou salve algo sem confirmacao humana.

Progresso das fases (ver README.md para o roteiro completo):
    FASE 1 - Enxergar janelas do Windows            -> implementada
    FASE 2 - Localizar a janela do SRI               -> implementada
    FASE 3 - Encontrar o campo de protocolo           -> pendente
    FASE 4 - Digitar protocolo de teste               -> pendente
    FASE 5 - Localizar o protocolo na tela            -> pendente
    FASE 6 - Selecionar escrevente                    -> pendente (exige confirmacao humana)
    FASE 7 - Salvar                                   -> pendente (exige confirmacao humana)
"""

import platform

from configuracao import MODO_SEGURO, TITULO_JANELA_SRI


class AutomacaoNaoDisponivelError(RuntimeError):
    """Levantado quando pywinauto/Windows nao estao disponiveis."""


def _garantir_windows() -> None:
    if platform.system() != "Windows":
        raise AutomacaoNaoDisponivelError(
            "rpa_sri.py depende do pywinauto (backend 'uia'), que só "
            "funciona no Windows. Rode este script na máquina do SRI."
        )


def listar_janelas() -> list[str]:
    """FASE 1: lista os titulos de todas as janelas abertas no Windows.

    Não clica em nada, não seleciona nada -- só enumera o que o
    pywinauto consegue enxergar, para confirmarmos que a automação
    "vê" o Windows corretamente.
    """
    _garantir_windows()
    from pywinauto import Desktop

    titulos = []
    for janela in Desktop(backend="uia").windows():
        try:
            titulo = janela.window_text()
        except Exception:
            continue
        if titulo:
            titulos.append(titulo)

    return titulos


def localizar_janela_sri(titulo_parcial: str = TITULO_JANELA_SRI):
    """FASE 2: localiza (sem clicar em nada) a janela cujo titulo contem
    `titulo_parcial`. Retorna o objeto da janela ou None se não achar.
    """
    _garantir_windows()
    from pywinauto import Desktop

    for janela in Desktop(backend="uia").windows():
        try:
            titulo = janela.window_text()
        except Exception:
            continue
        if titulo_parcial.lower() in titulo.lower():
            return janela

    return None


def _exigir_modo_nao_seguro(nome_fase: str) -> None:
    if MODO_SEGURO:
        raise AutomacaoNaoDisponivelError(
            f"{nome_fase} está bloqueada porque MODO_SEGURO está ativo. "
            "Só desative MODO_SEGURO no .env depois de validar manualmente "
            "as fases anteriores, uma de cada vez."
        )


def digitar_protocolo(protocolo: str):
    """FASE 4 (pendente): ainda não implementada -- precisamos primeiro
    mapear o campo de protocolo na Fase 3."""
    raise NotImplementedError("Fase 4 ainda não implementada.")


def selecionar_escrevente(nome_escrevente: str):
    """FASE 6 (pendente): seleção de escrevente. Mesmo quando implementada,
    deve sempre respeitar MODO_SEGURO e nunca salvar sozinha."""
    _exigir_modo_nao_seguro("Fase 6 (selecionar escrevente)")
    raise NotImplementedError("Fase 6 ainda não implementada.")


def salvar():
    """FASE 7 (pendente): salvar no SRI. Exige confirmação humana explícita
    antes de qualquer chamada real -- nunca deve rodar sem supervisão."""
    _exigir_modo_nao_seguro("Fase 7 (salvar)")
    raise NotImplementedError("Fase 7 ainda não implementada.")
