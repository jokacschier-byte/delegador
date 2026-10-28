# ferramenta_local_rpa (DistribuidorSRI)

Robô local que lê protocolos, aplica regras de simples/complexo/especial
e distribui os protocolos entre os escreventes no SRI (Sistema de
Registro de Imóveis) de um cartório específico.

## Princípio de segurança

Este projeto roda **100% local**. Nenhum CPF, nome, matrícula, documento,
protocolo ou dado de cliente é enviado para APIs externas de IA. A
classificação usa apenas regras programadas (`regras.py`).

O fluxo é:

```
SRI -> computador local -> algoritmo -> SRI
```

Além disso, `rpa_sri.py` tem um `MODO_SEGURO` (ligado por padrão) que
bloqueia qualquer ação de escrita (selecionar escrevente, salvar) até que
as fases anteriores tenham sido validadas manualmente por uma pessoa.

## Estrutura

```
ferramenta_local_rpa/
├── main.py            # ponto de entrada (linha de comando)
├── regras.py           # classificação por natureza (simples/complexo/especial)
├── distribuicao.py     # leitura/escrita da planilha e distribuição por carga
├── rpa_sri.py           # automação da interface do SRI (por fases)
├── configuracao.py      # caminhos, .env, MODO_SEGURO
├── dados/
│   └── protocolos.xlsx  # colunas: Protocolo, Natureza, Inventario (Sim/Nao),
│                         #          Grupo, Responsavel, Data, Status,
│                         #          Tempo Estimado (min), Observacao
└── logs/
```

## Instalação (Windows)

1. Instale o [Python](https://www.python.org/downloads/windows/) marcando
   **Add Python.exe to PATH**.
2. Instale o [Visual Studio Code](https://code.visualstudio.com/) e a
   extensão **Python** (Microsoft).
3. Clone este repositório e, dentro de `ferramenta_local_rpa/`:

   ```
   py -m pip install -r requirements.txt
   ```

4. Copie `.env.example` para `.env` e ajuste `TITULO_JANELA_SRI` se
   necessário. Mantenha `MODO_SEGURO=true` até validar as fases manualmente.

## Uso

```
py main.py listar-janelas   # Fase 1: lista as janelas abertas no Windows
py main.py localizar-sri    # Fase 2: tenta localizar a janela do SRI
py main.py classificar      # classifica dados/protocolos.xlsx por natureza
py main.py distribuir       # classifica e distribui entre os responsaveis (regras.py)
py main.py carga            # mostra a carga atual (em horas) de cada responsavel
```

Nenhum desses comandos clica ou salva algo no SRI.

## Roteiro de fases

| Fase | Objetivo | Status |
|---|---|---|
| 1 | Enxergar as janelas do Windows | ✅ implementada e validada |
| 2 | Localizar a janela do SRI | ✅ implementada e validada |
| 3 | Encontrar o campo de protocolo | pendente |
| 4 | Digitar protocolo de teste | pendente |
| 5 | Localizar o protocolo na tela | pendente |
| 6 | Selecionar escrevente | pendente (exige confirmação humana) |
| 7 | Salvar (com confirmação do usuário) | pendente (exige confirmação humana) |
| 8 | Automação completa | pendente |

`pywinauto`/`pyautogui` só funcionam no Windows — os comandos de
`rpa_sri.py` falham de forma explícita se rodados em outro sistema.

## Regras de competência

As regras completas (quem analisa o quê) estão documentadas e
comentadas em `regras.py`. Elas são as regras reais de um cartório
específico e servem de referência de domínio para o `saas/` deste
repositório, onde cada cliente cadastra as suas próprias.
