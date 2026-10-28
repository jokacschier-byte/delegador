# delegador

Este repositório contém dois produtos relacionados, mas com propósitos
diferentes:

## 1. `ferramenta_local_rpa/` — robô local para um cartório específico

Script Python que roda 100% local no computador de um cartório e
automatiza a distribuição de protocolos diretamente no SRI (Sistema
Registral Imobiliário da Mactus), via RPA (pywinauto/pyautogui).

As regras de competência nesse código são as regras reais do cartório
onde o projeto nasceu (ver `ferramenta_local_rpa/regras.py`). Ele serve
também como referência de domínio para o SaaS abaixo.

Detalhes de uso: `ferramenta_local_rpa/README.md` (ver histórico do
projeto) ou o código comentado em cada arquivo.

## 2. `saas/` — produto multi-tenant para vender a vários cartórios

Aplicação web (Django) onde cada cartório-cliente ("tenant") cadastra
sua própria equipe de escreventes e suas próprias naturezas de
protocolo (simples/complexo/urgente), e lança protocolos (número,
natureza, se é urgente) para receber automaticamente qual escrevente
deve analisar, com a carga de trabalho equilibrada entre a equipe.

**Sem RPA e sem integração com o SRI** — é só o motor de distribuição
inteligente, como um serviço web. Ver `saas/README.md` para instruções
de instalação e uso.
