"""
Configuracoes centrais do DistribuidorSRI.

Nada neste arquivo interage com o SRI. Ele apenas define caminhos,
constantes e o "modo seguro" que trava acoes automaticas de escrita
(selecionar escrevente / salvar) ate estarmos prontos para a Fase 6+.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DADOS_DIR = BASE_DIR / "dados"
LOGS_DIR = BASE_DIR / "logs"

DADOS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

PLANILHA_PROTOCOLOS = DADOS_DIR / "protocolos.xlsx"

COLUNAS_PROTOCOLOS = [
    "Protocolo",
    "Natureza",
    # Só preencher para "Carta de Adjudicação / Arrematação": Sim/Nao.
    # Para as demais naturezas, deixe em branco.
    "Inventario (Sim/Nao)",
    "Grupo",
    "Responsavel",
    "Data",
    "Status",
    "Tempo Estimado (min)",
    "Observacao",
]

# Titulo (ou parte dele) da janela do SRI, usado para localiza-la na Fase 2+.
TITULO_JANELA_SRI = os.getenv("TITULO_JANELA_SRI", "SRI")

# Enquanto MODO_SEGURO estiver ativo, qualquer funcao de rpa_sri.py que
# selecione escrevente ou salve algo deve recusar a executar. So mude
# isso no .env local, nunca direto no codigo, e somente quando as fases
# anteriores tiverem sido validadas manualmente.
MODO_SEGURO = os.getenv("MODO_SEGURO", "true").strip().lower() != "false"
