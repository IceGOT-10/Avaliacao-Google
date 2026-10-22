# review-redirect

Plataforma de redirecionamento e rastreamento de avaliações do Google via NFC/QR
(FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL).

## Pré-requisitos
- Python 3.12
- Docker e Docker Compose v2.24+ (para `!reset` no override de produção)

## Configuração
```bash
cp .env.example .env   # Windows PowerShell: Copy-Item .env.example .env
```
Edite `.env` (senhas reais nunca vão para o repositório).

### Principais Variáveis de Ambiente
- `DATABASE_URL`: String de conexão SQLAlchemy para PostgreSQL.
- `TEST_DATABASE_URL`: String de conexão para o banco de teste (deve terminar em `_test`).
- `SESSION_COOKIE_NAME`: Nome do cookie de sessão (padrão: `session_id`).
- `SESSION_TTL_HOURS`: Duração da sessão em horas (padrão: `12`).
- `COOKIE_SECURE`: Ativa flag `Secure` no cookie (padrão `true` em prod; `false` em dev local HTTP).
- `ALLOWED_ORIGINS`: Lista de origens permitidas para verificação de CSRF (separadas por vírgula).
- `LOGIN_RATE_LIMIT_MAX_ATTEMPTS`: Limite de falhas de login antes de bloqueio temporário 429 (padrão: `5`).
- `LOGIN_RATE_LIMIT_WINDOW_SECONDS`: Janela de contagem de falhas de login em segundos (padrão: `900` / 15 min).

## Instalação local (sem Docker)
```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

## Docker Compose
```bash
# Iniciar o banco de dados de desenvolvimento:
docker compose up -d db

# Iniciar aplicação completa:
docker compose up --build
curl http://localhost:8000/health
```

## Linha de Comando (CLI)
### Criação de Administrador
O primeiro administrador deve ser criado via CLI interativa (a senha é lida via `getpass` com confirmação e nunca passada por argumento nem logada):
```bash
python -m app.cli create-admin --email admin@empresa.com
```

## Rotas Principais
- `GET /health`: Liveness check (retorna `{"status": "ok"}` sem tocar no banco de dados).
- `GET /r/{code}`: Endpoint público de redirecionamento (HTTP 307 Temporary Redirect).
  - Resolve o link ativo por `code`.
  - Valida o destino contra a allowlist estrita do Google Meu Negócio / Google Maps (anti-open-redirect).
  - Registra um evento de auditoria (`access_events`) de forma resiliente e anônima (sem dados pessoais, IP ou UA bruto).
  - Retorna `Cache-Control: no-store` para impedir cacheamento indevido no cliente/navegador.
  - Links desativados respondem HTTP 410 Gone; códigos inválidos ou inexistentes respondem HTTP 404 Not Found.
- `POST /auth/login`: Autenticação via JSON (`{email, password}`). Emite cookie de sessão server-side `HttpOnly` com `SameSite=Lax`.
- `POST /auth/logout`: Revoga a sessão no banco e remove o cookie (HTTP 204 No Content, idempotente).
- `GET /auth/me`: Retorna os dados do usuário autenticado a partir do cookie da sessão (`{id, email, is_admin}`).

## Migrações (Alembic)
As migrações não rodam automaticamente no startup do container. A execução deve ser explícita:
```bash
# Via Docker:
docker compose run --rm app alembic upgrade head

# Localmente (com o banco ativo):
alembic upgrade head
alembic downgrade base
alembic check
```

## Testes Automatizados
```bash
# Testes rápidos de rotas (não dependem do PostgreSQL):
pytest tests/test_health.py

# Testes unitários do validador anti-open-redirect:
pytest tests/test_url_validator.py -v

# Testes unitários de hashing de senhas e segurança:
pytest tests/test_security.py -v

# Testes de autenticação e sessão com banco real:
pytest tests/test_auth.py -v

# Suíte completa de integridade e rotas com banco real (requer PostgreSQL e TEST_DATABASE_URL):
# Por segurança, o nome do banco de teste deve terminar obrigatoriamente em _test
pytest -v
```

## Produção
```bash
docker compose -f compose.yaml -f compose.production.yaml config   # validar
docker compose -f compose.yaml -f compose.production.yaml up -d --build
```
O override remove `--reload`, volumes de código e a porta do banco, usa `restart: unless-stopped`
e exige `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` no ambiente/secret manager.
