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

## Migrações (Alembic)
As migrações não rodam automaticamente no startup do container. A execução deve ser explícita:
```bash
# Via Docker:
docker compose run --rm app alembic upgrade head

# Localmente (com o banco ativo):
alembic upgrade head
alembic downgrade base
```

## Testes Automatizados
```bash
# Testes rápidos de rotas (não dependem do PostgreSQL):
pytest tests/test_health.py

# Suíte completa de integridade (requer PostgreSQL rodando e TEST_DATABASE_URL configurada):
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

## Suposições e Decisões Técnicas
- Nome do projeto `review-redirect` (placeholder), porta 8000, banco `review_redirect`.
- Driver `psycopg` 3 (`postgresql+psycopg://`).
- Naming convention explícita para constraints do SQLAlchemy/Alembic.