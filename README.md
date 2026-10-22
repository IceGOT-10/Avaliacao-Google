# review-redirect

Base técnica da plataforma de redirecionamento de avaliações do Google via NFC/QR
(FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL). Sem regras de negócio nesta etapa.

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
Requer um PostgreSQL acessível em `DATABASE_URL` apenas para migrações; o `/health` e os testes não precisam dele.

## Docker Compose
```bash
docker compose up --build
curl http://localhost:8000/health
```

## Migrações (comando explícito; não rodam no startup)
```bash
docker compose run --rm app alembic upgrade head
# local: alembic upgrade head
```

## Testes
```bash
pytest
```
Não dependem do PostgreSQL.

## Produção
```bash
docker compose -f compose.yaml -f compose.production.yaml config   # validar
docker compose -f compose.yaml -f compose.production.yaml up -d --build
```
O override remove `--reload`, volumes de código e a porta do banco, usa `restart: unless-stopped`
e exige `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` no ambiente/secret manager.

## Suposições
- Nome do projeto `review-redirect` (placeholder), porta 8000, banco `review_redirect`.
- Driver `psycopg` 3 (`postgresql+psycopg://`).
