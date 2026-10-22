# review-redirect

Plataforma de redirecionamento e rastreamento de avalia??es do Google via NFC/QR
(FastAPI + SQLAlchemy 2.x + Alembic + PostgreSQL).

## Pr?-requisitos
- Python 3.12
- Docker e Docker Compose v2.24+ (para `!reset` no override de produ??o)

## Configura??o
```bash
cp .env.example .env   # Windows PowerShell: Copy-Item .env.example .env
```
Edite `.env` (senhas reais nunca v?o para o reposit?rio).

## Instala??o local (sem Docker)
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

# Iniciar aplica??o completa:
docker compose up --build
curl http://localhost:8000/health
```

## Rotas Principais
- `GET /health`: Liveness check (retorna `{"status": "ok"}` sem tocar no banco de dados).
- `GET /r/{code}`: Endpoint p?blico de redirecionamento (HTTP 307 Temporary Redirect).
  - Resolve o link ativo por `code`.
  - Valida o destino contra a allowlist estrita do Google Meu Neg?cio / Google Maps (anti-open-redirect).
  - Registra um evento de auditoria (`access_events`) de forma resiliente e an?nima (sem dados pessoais, IP ou UA bruto).
  - Retorna `Cache-Control: no-store` para impedir cacheamento indevido no cliente/navegador.
  - Links desativados respondem HTTP 410 Gone; c?digos inv?lidos ou inexistentes respondem HTTP 404 Not Found.

### Testando o Redirecionamento Manualmente
```bash
# Teste via curl sem seguir o redirecionamento (exibe o cabe?alho Location e status 307):
curl -i http://localhost:8000/r/SEU_CODIGO_AQUI
```

## Migra??es (Alembic)
As migra??es n?o rodam automaticamente no startup do container. A execu??o deve ser expl?cita:
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
# Testes r?pidos de rotas (n?o dependem do PostgreSQL):
pytest tests/test_health.py

# Testes unit?rios do validador anti-open-redirect:
pytest tests/test_url_validator.py -v

# Su?te completa de integridade e rotas com banco real (requer PostgreSQL e TEST_DATABASE_URL):
# Por seguran?a, o nome do banco de teste deve terminar obrigatoriamente em _test
pytest -v
```

## Produ??o
```bash
docker compose -f compose.yaml -f compose.production.yaml config   # validar
docker compose -f compose.yaml -f compose.production.yaml up -d --build
```
O override remove `--reload`, volumes de c?digo e a porta do banco, usa `restart: unless-stopped`
e exige `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` no ambiente/secret manager.

## Suposi??es e Decis?es T?cnicas
- Nome do projeto `review-redirect`, porta 8000, banco `review_redirect`.
- Driver `psycopg` 3 (`postgresql+psycopg://`).
- Naming convention expl?cita para constraints do SQLAlchemy/Alembic.
- Valida??o estrita de URLs de destino baseada na [documenta??o oficial do Google](https://support.google.com/business/answer/16816815?hl=pt-BR).
