# saas — Distribuidor de Protocolos (multi-tenant)

Aplicação web (Django) de distribuição inteligente de protocolos para
cartórios. Cada cartório-cliente ("tenant") configura sua própria
equipe de escreventes e suas próprias naturezas de protocolo, e lança
protocolos (número, natureza, matrículas, partes, se é urgente) para
saber automaticamente qual escrevente deve analisar — com a carga de
trabalho equilibrada entre a equipe, respeitando férias e um rodízio
de urgentes.

**Sem RPA.** A única integração com o SRI é de via planilha exportada
manualmente (ver "Sincronizar SRI" abaixo) — nunca controle direto da
interface do sistema do cartório.

## Modelo de dados

- **Cartorio**: o tenant. Tudo abaixo pertence a exatamente um cartório.
- **Perfil**: liga um usuário (login) a um cartório.
- **Escrevente**: uma pessoa da equipe daquele cartório.
- **Grupo**: um grupo de competência definido pelo cliente (ex.:
  "Simples", "Complexo"), com os escreventes que podem receber
  protocolos desse grupo, e os pesos extras por matrícula/parte além
  da primeira (`peso_extra_matricula_dias`, `peso_extra_parte_dias`).
- **Natureza**: um tipo de protocolo (ex.: "Carta de Adjudicação"),
  mapeado para um Grupo e com um peso base em dias
  (`peso_base_dias`). Pode ter um `grupo_se_inventario` opcional —
  quando preenchido, o formulário "Lançar protocolo" pergunta "É
  inventário?" e usa esse grupo (e os pesos dele) em vez do padrão.
- **Protocolo**: número + natureza + matrículas + partes + urgente,
  lançado por um usuário; ganha `peso_dias` (calculado no lançamento) e
  um `escrevente_responsavel` automaticamente. Tem `status` (Em
  aberto/Concluído/Diligência) e `tipo` (Novo/Reingresso).
- **Ferias**: um período (início/fim) de férias de um escrevente.

A distribuição (`nucleo/distribuicao.py`) escolhe, dentro do grupo
efetivo da natureza (considerando o toggle de inventário), o escrevente
ativo com:
1. Disponibilidade (não bloqueado por férias para esse tipo de
   protocolo — novo ou reingresso; se isso esvaziar o grupo inteiro, a
   regra de férias é ignorada como rede de segurança);
2. Prioridade de rodízio, se o protocolo é urgente (quem ainda não
   recebeu nenhum urgente nesta "rodada" do grupo, até todo mundo ter
   recebido um e a rodada resetar);
3. Menor carga atual — soma de `peso_dias` só dos protocolos com
   `status=ABERTO` (não é mais uma janela de tempo artificial: a carga
   cai de verdade quando o status muda para Concluído/Diligência, no
   Histórico ou pela sincronização com o SRI).

Essa lógica replica o app local (Flask + SQLite) já validado em
produção por um cartório real, só que configurável por banco em vez de
fixa no código, para atender vários clientes.

## Isolamento entre clientes (multi-tenant)

- Toda tabela (exceto Cartorio/Perfil) tem uma FK para `Cartorio`.
- As views (`views.py`) sempre filtram pelo cartório do usuário logado
  (`request.user.perfil.cartorio`).
- O Django Admin usado como tela de configuração (`admin.py`) tem um
  `TenantScopedAdmin` que filtra automaticamente por cartório e escreve
  o cartório sozinho ao salvar — o campo fica oculto para quem não é
  superuser.
- Um usuário comum (criado via `criar_cartorio`) só tem permissão nos
  modelos `Escrevente`, `Grupo`, `Natureza` e `Protocolo` — nunca em
  `Cartorio` ou `Perfil` de ninguém.
- Isso é testado em `nucleo/tests.py` (`IsolamentoEntreCartoriosTests`).

## Instalação (desenvolvimento local)

```
cd saas
py -m pip install -r requirements.txt
copy .env.example .env      (Windows)   ou   cp .env.example .env   (Linux/Mac)
py manage.py migrate
```

## Criar o primeiro cartório-cliente

```
py manage.py criar_cartorio --nome "Nome do Cartório" --usuario admin_cartorio --senha "uma-senha-forte"
```

Isso cria o tenant, o usuário administrador dele (com acesso só aos
próprios dados) e já aplica as permissões corretas. Por padrão, também
pré-carrega o **catálogo padrão** de grupos e naturezas (ver abaixo) —
use `--sem-catalogo-padrao` para começar com um cartório totalmente
vazio.

## Catálogo padrão de grupos/naturezas

`nucleo/dados_padrao.py` tem a lista de Grupos (Simples, Complexo,
Consolidação/Notificação, Especial — com os pesos extras por
matrícula/parte já calibrados) e ~90 Naturezas já mapeadas para cada
um, com peso base em dias. Isso é carregado automaticamente em todo
cartório novo.

**O que NÃO é padrão**: nenhum Escrevente é criado automaticamente —
cada cartório-cliente tem sua própria equipe, cadastrada por ele em
`/admin/nucleo/escrevente/` e distribuída entre os grupos existentes
(`/admin/nucleo/grupo/`). O cliente também pode renomear grupos, ajustar
pesos, ou adicionar naturezas próprias à vontade — o catálogo é só um
ponto de partida, não é fixo.

Para carregar (ou recarregar, sem duplicar) o catálogo padrão num
cartório que já existe:

```
py manage.py carregar_catalogo_padrao --usuario admin_cartorio
```

## Rodar localmente

```
py manage.py runserver
```

Acesse:
- `http://127.0.0.1:8000/` — painel (carga da equipe)
- `http://127.0.0.1:8000/protocolos/novo/` — lançar protocolo
- `http://127.0.0.1:8000/historico/` — histórico de designações (e troca manual de status)
- `http://127.0.0.1:8000/ferias/` — cadastro de períodos de férias
- `http://127.0.0.1:8000/sincronizar/` — importar planilha do SRI (ainda não implementado)
- `http://127.0.0.1:8000/admin/` — configuração (escreventes, grupos, naturezas, pesos)

## Rodar os testes

```
py manage.py test nucleo
```

## Deploy em produção (Railway)

O projeto já está pronto pra isso: `gunicorn` + `whitenoise` (estáticos)
+ `dj-database-url` (Postgres via `DATABASE_URL`) + `Procfile` +
`nixpacks.toml` (faz o `collectstatic` rodar no build).

1. No [Railway](https://railway.app), crie um projeto novo a partir
   deste repositório GitHub.
2. Em **Settings → Root Directory**, aponte para `saas` (o projeto
   Django não está na raiz do repo).
3. Adicione um serviço **Postgres** ao projeto (Railway preenche a
   variável `DATABASE_URL` sozinho quando os dois serviços estão
   linkados).
4. Configure as variáveis de ambiente do serviço web:
   - `DJANGO_SECRET_KEY` — uma chave aleatória longa (nunca a de dev).
   - `DJANGO_DEBUG=false`
   - `DJANGO_ALLOWED_HOSTS` — o domínio do Railway (ex.
     `registrai.up.railway.app`) e/ou o domínio próprio depois de
     configurado.
   - `DJANGO_CSRF_TRUSTED_ORIGINS` — a mesma coisa, com `https://` na
     frente (ex. `https://registrai.up.railway.app`).
5. Deploy. O Railway builda (rodando `collectstatic` via
   `nixpacks.toml`), depois roda `release: python manage.py migrate`
   e sobe o `web: gunicorn config.wsgi` do `Procfile`.
6. Crie o primeiro cartório-cliente rodando, no terminal do Railway
   (ou localmente apontando `DATABASE_URL` pro Postgres de produção):
   `python manage.py criar_cartorio --nome "..." --usuario ... --senha ...`

## O que falta para produção (próximos passos, não feito ainda)

- **Sincronizar SRI**: a tela existe (`/sincronizar/`) mas a importação
  da planilha (.xlsx exportado do SRI) ainda não foi implementada —
  por enquanto, o status dos protocolos é trocado manualmente no
  Histórico.
- **Cadastro automático após pagamento**: hoje `criar_cartorio` é
  manual, no terminal. Para o cliente pagar e receber o link sozinho,
  falta (a) uma página pública de preços/cadastro fora da área logada,
  (b) integração com um meio de pagamento (Asaas/Pagar.me/Iugu são os
  cotados, por aceitarem assinatura recorrente com boleto/PIX/cartão
  no Brasil), (c) um webhook que recebe a confirmação de pagamento e
  chama a criação do cartório automaticamente, e (d) envio de e-mail
  com o link de acesso (precisa de um serviço de envio, ex. Resend,
  SendGrid, Mailgun, Amazon SES).
- Tela de cadastro self-service para novos clientes (ligada ao item
  acima).
- Página inicial de marketing (landing page) separada da área logada.
- Domínio próprio (hoje aponta só para o subdomínio do Railway).
