# saas — Distribuidor de Protocolos (multi-tenant)

Aplicação web (Django) de distribuição inteligente de protocolos para
cartórios. Cada cartório-cliente ("tenant") configura sua própria
equipe de escreventes e suas próprias naturezas de protocolo, e lança
protocolos (número, natureza, se é urgente) para saber automaticamente
qual escrevente deve analisar — com a carga de trabalho equilibrada
entre a equipe.

**Sem RPA, sem integração com nenhum sistema de cartório.** É só o
motor de distribuição, como um serviço web.

## Modelo de dados

- **Cartorio**: o tenant. Tudo abaixo pertence a exatamente um cartório.
- **Perfil**: liga um usuário (login) a um cartório.
- **Escrevente**: uma pessoa da equipe daquele cartório.
- **Grupo**: um grupo de competência definido pelo cliente (ex.:
  "Simples", "Complexo"), com os escreventes que podem receber
  protocolos desse grupo.
- **Natureza**: um tipo de protocolo (ex.: "Averbação de Divórcio"),
  mapeado para um Grupo e com um tempo estimado padrão (minutos).
- **Protocolo**: número + natureza + urgente, lançado por um usuário;
  ganha automaticamente um `escrevente_responsavel` ao ser distribuído.

A distribuição (`nucleo/distribuicao.py`) escolhe, dentro do grupo da
natureza, o escrevente ativo com menor carga total estimada (soma dos
`tempo_estimado_minutos` dos protocolos já atribuídos a ele) — mesma
lógica usada em `ferramenta_local_rpa/distribuicao.py`, só que a equipe
e as regras vêm do banco, configuráveis por cada cliente.

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

`nucleo/dados_padrao.py` tem a lista de Grupos (Simples, Notificação
para Consolidação, Complexo, Usucapião e Adjudicação Compulsória) e
~70 Naturezas já mapeadas para cada um, com tempo estimado — a mesma
classificação validada em `ferramenta_local_rpa/regras.py`. Isso é
carregado automaticamente em todo cartório novo.

**O que NÃO é padrão**: nenhum Escrevente é criado automaticamente —
cada cartório-cliente tem sua própria equipe, cadastrada por ele em
`/admin/nucleo/escrevente/` e distribuída entre os grupos existentes
(`/admin/nucleo/grupo/`). O cliente também pode renomear grupos, ajustar
tempos estimados, ou adicionar naturezas próprias à vontade — o
catálogo é só um ponto de partida, não é fixo.

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
- `http://127.0.0.1:8000/` — painel (carga da equipe + lançar protocolo)
- `http://127.0.0.1:8000/admin/` — configuração (escreventes, grupos, naturezas)

## Rodar os testes

```
py manage.py test nucleo
```

## O que falta para produção (próximos passos, não feito ainda)

- Banco de dados de produção (Postgres) em vez de SQLite.
- Deploy real (ex.: Railway, Render, Fly.io) com `DEBUG=false`,
  `DJANGO_SECRET_KEY` forte e `DJANGO_ALLOWED_HOSTS` configurado.
- Tela de cadastro self-service para novos clientes (hoje é via
  `criar_cartorio` no terminal, feito pela equipe do SaaS).
- Cobrança/assinatura.
- Página inicial de marketing (landing page) separada da área logada.
- Dar um uso real ao campo `urgente` na distribuição (hoje ele só é
  guardado e exibido, não afeta a escolha do escrevente).
