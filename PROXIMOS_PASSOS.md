# Status do projeto e próximos passos

Resumo de onde paramos, pra continuar depois sem precisar reler tudo.
Todo o código já está salvo e no GitHub — isso aqui é só o "estado da
mente" da conversa: o que foi decidido, o que está pronto e o que
falta.

## Como retomar

- **A conversa inteira continua acessível**: abra
  `https://claude.ai/code/session_01XbNm9gQqupQqwP6cHZkcdA` de
  qualquer computador logado na sua conta — é a mesma sessão, com todo
  o histórico, não precisa reexplicar nada.
- **O código está na branch** `claude/rpa-python-automation-8lzj8y`
  do repositório `jokacschier-byte/delegador`. Pra continuar em casa:
  ```
  git clone https://github.com/jokacschier-byte/delegador.git
  cd delegador
  git checkout claude/rpa-python-automation-8lzj8y
  ```

## O que já está pronto

1. **`ferramenta_local_rpa/`** — robô local (Python) que já roda de
   verdade no cartório, distribuindo protocolos direto no SRI.
2. **`saas/`** — o produto novo, pra vender pra outros cartórios:
   - Multi-tenant (cada cartório-cliente só vê os próprios dados),
     testado (47 testes automatizados, todos passando).
   - Motor de distribuição com a lógica real do cartório: peso em
     dias por natureza + ajuste por matrícula/parte extra, regras de
     férias, rodízio de urgentes, toggle de inventário.
   - Telas: Painel, Lançar protocolo, Histórico, Férias, Sincronizar
     SRI (placeholder), Configurações (Django Admin).
   - Identidade visual da marca **registrai** aplicada (logos, cores
     navy/dourado, favicon) em todo o app, inclusive no Admin.
   - Revisão de design/UX feita com a skill `design-taste-frontend`
     (contraste corrigido, alinhamento de tabelas, título de página em
     cada tela, etc.) — ver commits recentes na branch.
   - **Pronto pra deploy em produção**: `gunicorn` + `whitenoise` +
     `dj-database-url` (Postgres) + `Procfile` + `nixpacks.toml`, tudo
     testado localmente simulando produção.

## O que falta (decisões já tomadas, execução pendente)

### 1. Deploy no Railway — só você consegue fazer essa parte

Passo a passo completo já está em `saas/README.md`, seção "Deploy em
produção (Railway)". Resumo:

1. Criar projeto no [railway.app](https://railway.app) a partir deste
   repositório GitHub.
2. Settings → Root Directory → `saas`.
3. Adicionar um serviço Postgres ao projeto.
4. Configurar as variáveis de ambiente (`DJANGO_SECRET_KEY`,
   `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS`,
   `DJANGO_CSRF_TRUSTED_ORIGINS`) — valores exatos no README.
5. Deploy. Depois disso você tem um link real pra abrir no navegador.

### 2. Cobrança automática (cliente paga → recebe o link sozinho)

Decisões já tomadas na conversa:
- **Hospedagem**: Railway.
- **Pagamento**: família Asaas / Pagar.me / Iugu (processadores
  brasileiros com assinatura recorrente — boleto/PIX/cartão). Ainda
  **falta escolher qual dos três** e criar a conta.

O que falta construir (ninguém começou ainda):
- Página pública de preços/cadastro, fora da área logada.
- Integração com o processador escolhido (checkout de assinatura).
- Um webhook que recebe a confirmação de pagamento e chama a criação
  automática do cartório (hoje isso é manual, via comando
  `criar_cartorio` no terminal).
- Envio de e-mail com o link de acesso (precisa de um serviço de
  envio: Resend, SendGrid, Mailgun ou Amazon SES).

**Pra continuar essa parte**, a próxima sessão vai precisar que você:
1. Escolha Asaas, Pagar.me ou Iugu e crie a conta.
2. Traga a chave de API (sandbox/teste primeiro, não a de produção).

### Outros itens, sem pressa (listados no `saas/README.md`)

- Sincronizar SRI (importar planilha, hoje é manual no Histórico).
- Domínio próprio (hoje seria só o subdomínio do Railway).
- Página inicial de marketing (landing page).
