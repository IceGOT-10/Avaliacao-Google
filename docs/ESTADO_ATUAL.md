# Estado atual do projeto

## 1. Última auditoria
- **Data e hora local:** 22 de outubro de 2026, 17:28 (Horário de Brasília, UTC-03:00).
- **Branch atual:** `main`.
- **Commit base (HEAD):** `a67e935` (*first commit*).
- **Estado do Git:**
  - 7 arquivos modificados no working tree (não commitados): `.env.example`, `README.md`, `app/core/config.py`, `app/core/database.py`, `app/models/__init__.py`, `migrations/env.py`, `tests/conftest.py`.
  - 10 arquivos/diretórios não rastreados (*untracked*): `AGENTS.md`, `app/core/tokens.py`, `app/models/access_event.py`, `app/models/business.py`, `app/models/business_membership.py`, `app/models/review_link.py`, `app/models/review_snapshot.py`, `app/models/user.py`, `docs/`, `migrations/versions/0001_initial_schema.py`, `tests/test_models.py`.
  - Total de arquivos alterados/criados referentes à Fase 2 prontos para validação e commit pelo usuário.
- **Limitações da inspeção:**
  - Execução realizada no ambiente de desenvolvimento local Windows 11 (PowerShell) utilizando o ambiente virtual Python 3.12 (`.venv`).
  - Container PostgreSQL 16 (`avaliacaogoogle-db-1`) ativo no Docker Compose, mapeado na porta `5433` do host para desenvolvimento e testes.
  - Comandos do Alembic executados exclusivamente em modo de leitura/inspeção (`current`, `heads`, `check`), sem operações de DDL destrutivas.

---

## 2. Fase atual
- **Número e nome da fase:**
  - **Fase 1 — Fundação técnica e ambiente reproduzível:** CONCLUÍDA.
  - **Fase 2 — Modelo de dados e migrações:** CONCLUÍDA.
  - **Fase 3 — Fluxo público NFC/QR e redirecionamento:** NÃO INICIADA (próxima etapa).
- **Estado:** EM TRANSIÇÃO (Fases 1 e 2 concluídas, Fase 3 pronta para início).
- **Justificativa baseada em evidências desta auditoria:**
  - `alembic current` executado contra o PostgreSQL de desenvolvimento confirmou a revisão `0001_initial_schema (head)`.
  - `alembic check` confirmou zero divergências entre o metadata dos modelos declarativos e o schema do banco (`No new upgrade operations detected.`, exit code 0).
  - Execução de `pytest -v` confirmou 15/15 testes passando, cobrindo todas as constraints de integridade relacional, unicidades e regras de exclusão no PostgreSQL real.
- **Objetivo imediato:** Iniciar a Fase 3, implementando o endpoint público `GET /r/{code}`, o serviço de validação estrita anti-open-redirect (apenas URLs legítimas do Google) e a persistência de eventos em `access_events`.

---

## 3. Funcionalidades verificadas

| Funcionalidade | Arquivos relevantes | Estado | Evidência disponível (sessão atual) |
| :--- | :--- | :--- | :--- |
| **Health Check (`GET /health`)** | `app/main.py`, `app/api/health.py`, `tests/test_health.py` | Implementada e verificada | Responde HTTP 200 `{"status": "ok"}` no `pytest` isolado sem banco. |
| **Configuração de Ambiente** | `app/core/config.py`, `.env.example`, `.env` | Implementada e verificada | `pydantic-settings` carrega variáveis de ambiente; verificado suporte a `TEST_DATABASE_URL`. |
| **Conexão e Naming Convention** | `app/core/database.py` | Implementada e verificada | `POSTGRES_NAMING_CONVENTION` registrada em `Base.metadata` e validada nas constraints do Alembic. |
| **Geração Segura de Códigos** | `app/core/tokens.py`, `tests/test_models.py` | Implementada e verificada | `generate_link_code` testado com geração em lote de 1.000 tokens únicos via `pytest`. |
| **Modelos de Dados (6 entidades)** | `app/models/*`, `app/models/__init__.py` | Implementada e verificada | Modelos declarativos SQLAlchemy 2.x com tipagem `Mapped`/`mapped_column` validados em 14 testes de integração. |
| **Migração Inicial do Schema** | `migrations/versions/0001_initial_schema.py` | Implementada e verificada | `alembic current` = `0001_initial_schema`, `alembic check` = exit 0 sem novas operações pendentes. |
| **Ambiente Docker / Compose** | `Dockerfile`, `compose.yaml`, `compose.production.yaml` | Implementada e verificada | Container `avaliacaogoogle-db-1` inspecionado ativo e saudável via `docker compose ps`. |
| **Redirecionamento Público `/r/{code}`** | N/A | Ausente | Rota não criada em `app/api/` (escopo da Fase 3). |
| **Validação Anti-Open Redirect** | N/A | Ausente | Validação estrita de domínio do Google ainda não implementada (escopo da Fase 3). |
| **Autenticação e Autorização** | N/A | Ausente | Sem autenticação de lojistas implementada (escopo da Fase 4). |
| **Métricas e Painel de Acessos** | N/A | Ausente | Sem endpoints de métricas ou agregações (escopo da Fase 5). |
| **Geração de QR Code e NFC** | N/A | Ausente | Sem utilitários de geração de imagens de QR Code (escopo da Fase 6). |

---

## 4. Banco de dados e infraestrutura
- **Banco de Dados Afetado nas Leituras do Alembic:**
  - Banco de desenvolvimento: `review_redirect` (host `localhost:5433`, usuário `app_user`).
  - Comando `alembic current`: `0001_initial_schema (head)`.
  - Comando `alembic heads`: `0001_initial_schema (head)`.
  - Comando `alembic check`: `No new upgrade operations detected.` (exit 0).
- **Banco de Testes Separado:**
  - Banco de testes: `review_redirect_test` (host `localhost:5433`, usuário `app_user`).
  - Validado via fixture `get_verified_test_db_url()` em `tests/conftest.py` que aborta caso o banco não termine com `_test`.
- **Tabelas Operacionais (6 entidades):**
  - `users`: `id` (BigInt PK), `email` (único, minúsculo forçado por `CheckConstraint`), `password_hash`, `is_active`, `is_admin`, timestamps.
  - `businesses`: `id` (BigInt PK), `name`, `slug` (único), `google_review_url`, `timezone` (default 'America/Sao_Paulo'), `is_active`, timestamps. *Sem campo de endereço.*
  - `business_memberships`: `id` (BigInt PK), `user_id` (FK cascade), `business_id` (FK cascade), `role` (Check: 'owner'/'manager'), `created_at`. Unique(user_id, business_id).
  - `review_links`: `id` (BigInt PK), `business_id` (FK restrict), `code` (único), `source` (Check: 'nfc'/'qr'/'other'), `label`, `destination_url` (Check: começa com https://), `is_active`, timestamps, `deactivated_at`.
  - `access_events`: `id` (BigInt PK), `review_link_id` (FK restrict), `occurred_at`, `result` (Check: 'redirected'/'blocked_inactive'), `is_probable_bot`. Sem IP, sem UA bruto e sem geolocalização.
  - `review_snapshots`: `id` (BigInt PK), `business_id` (FK restrict), `captured_at`, `total_reviews` (Check: >= 0), `average_rating` (Numeric(3,2), Check: 0 a 5), `source` (Check: 'manual'/'google_api'), `status`, `error_message`.
- **Infraestrutura Docker:**
  - `compose.yaml`: postgres 16-alpine com healthcheck operacional (`Up 3 minutes (healthy)`).
  - Porta do host em desenvolvimento: `DB_HOST_PORT=5433` (evitando conflito com a porta padrão 5432).

---

## 5. Testes
- **Testes existentes:**
  - `tests/test_health.py::test_health_returns_ok` (liveness check isolado sem dependência de banco).
  - `tests/test_models.py::test_entities_creation_and_relationships` (criação e navegação bidirecional).
  - `tests/test_models.py::test_user_email_uniqueness` (unicidade de email).
  - `tests/test_models.py::test_business_slug_uniqueness` (unicidade de slug).
  - `tests/test_models.py::test_review_link_code_uniqueness` (unicidade de código de link).
  - `tests/test_models.py::test_business_membership_uniqueness` (unicidade da associação user-business).
  - `tests/test_models.py::test_user_email_lowercase_check_constraint` (CheckConstraint de email minúsculo).
  - `tests/test_models.py::test_business_membership_role_check_constraint` (CheckConstraint de role: 'owner'/'manager').
  - `tests/test_models.py::test_review_link_source_check_constraint` (CheckConstraint de source: 'nfc'/'qr'/'other').
  - `tests/test_models.py::test_review_link_destination_url_https_check_constraint` (CheckConstraint de URL https).
  - `tests/test_models.py::test_access_event_result_check_constraint` (CheckConstraint de resultado: 'redirected'/'blocked_inactive').
  - `tests/test_models.py::test_review_snapshot_check_constraints` (CheckConstraints de rating 0-5, total >= 0 e source).
  - `tests/test_models.py::test_ondelete_restrict_for_business_and_links` (RESTRICT protegendo histórico analítico).
  - `tests/test_models.py::test_ondelete_cascade_for_memberships` (CASCADE de memberships ao excluir usuário ou loja).
  - `tests/test_models.py::test_generate_link_code_uniqueness_and_format` (geração em lote de 1.000 tokens únicos).
- **Comandos efetivamente executados nesta auditoria:**
  ```powershell
  .\.venv\Scripts\python -m pytest -v
  ```
- **Resultados observados:**
  - **15 aprovados, 0 falhos** em 1.12s.
  - 1 warning de depreciação de `anyio` na biblioteca `starlette` (aviso interno do TestClient do Starlette, sem impacto funcional).
- **Testes não executados:**
  - Testes de concorrência massiva de conexões: não executados por não fazerem parte do escopo de testes unitários/integrados da Fase 2.
- **Falhas e riscos pendentes:**
  - Nenhuma falha identificada. A suíte completa está verde e determinística.

---

## 6. Segurança
- **Proteção de Segredos:** Conforme. Nenhuma senha, token ou string de conexão com credencial real está versionada no Git ou em arquivos de código. O `.env` está estritamente listado em `.gitignore` e `.dockerignore`.
- **Integridade e Prevenção de Perda de Dados:** O uso de `ondelete="RESTRICT"` em `review_links`, `access_events` e `review_snapshots` protege contra a perda acidental de histórico de métricas quando um lojista for manipulado.
- **Privacidade por Design:** O modelo `access_events` cumpre a diretriz de não armazenar dados pessoais rastreáveis (sem IP, sem User-Agent bruto, sem fingerprint, sem geolocalização).
- **Validação de Destinos (Anti-Open Redirect):**
  - Implementado no nível do banco via `CheckConstraint("destination_url LIKE 'https://%'")`.
  - Pendente para a Fase 3: validação de domínio em nível de aplicação (permitindo estritamente domínios oficiais do Google: `g.page/r/...`, `search.google.com/local/writereview?...`, `maps.app.goo.gl/...`, `google.com/maps/...`).

---

## 7. Pendências priorizadas

### P0 — Bloqueadores críticos
- *Nenhum bloqueador crítico.* Base de dados, modelos e migrações validados e operacionais.

### P1 — Necessários para a próxima etapa (Fase 3)
1. **Endpoint Público `GET /r/{code}`:**
   - Consulta do link ativo por `code`.
   - Se ativo: redirecionamento HTTP 307 (Temporary Redirect) e persistência de `access_event` com `result='redirected'`.
   - Se inativo (`is_active=False` ou `deactivated_at` não nulo): resposta amigável (ou HTTP 410/404) e persistência de `access_event` com `result='blocked_inactive'`.
   - Se inexistente: retorno HTTP 404 (sem gravar evento em banco).
2. **Serviço de Validação Anti-Open Redirect:**
   - Serviço ou validador em `app/services/` para assegurar que apenas URLs do Google Meu Negócio possam ser cadastradas e redirecionadas.
3. **Detecção Básica de Bots:**
   - Identificação de bots conhecidos via User-Agent para preencher a flag booleana `is_probable_bot` (sem armazenar o User-Agent).

### P2 — Melhorias posteriores (Fases 4 a 6)
1. Autenticação e autorização com JWT para lojistas (Fase 4).
2. API de métricas e relatórios agregados por ponto físico (Fase 5).
3. Geração de QR Code em imagem (SVG/PNG) e payloads para gravação NFC (Fase 6).

---

## 8. Próxima tarefa recomendada
- **Objetivo:** Implementar a **Fase 3 — Fluxo público NFC/QR e redirecionamento**.
- **Arquivos prováveis afetados:**
  - `app/api/redirect.py` (novo router para `/r/{code}`)
  - `app/services/redirect_service.py` (lógica de consulta, auditoria e detecção básica de bot)
  - `app/services/url_validator.py` (validador estrito de domínios Google)
  - `app/main.py` (inclusão do novo router)
  - `tests/test_redirect.py` (novos testes de fluxo público)
- **Critérios de aceitação:**
  - Rota `GET /r/{code}` executando redirecionamento HTTP 307 para a URL cadastrada.
  - Links desativados barrados com registro `blocked_inactive`.
  - Códigos inexistentes retornando HTTP 404 sem gravação de evento.
  - Evento de acesso gravado sem dados sensíveis (sem IP ou UA bruto).
  - Validador de URL rejeitando domínios fora da lista de permissões do Google Meu Negócio.
- **Testes necessários:**
  - Teste de redirecionamento com link ativo (HTTP 307 + Location header correto).
  - Teste de link inativo e link inexistente.
  - Teste de auditoria de eventos criados no banco.
  - Teste unitário do validador de URL contra tentativas de Open Redirect.
- **Dependências e riscos:**
  - Garantir tempo de resposta baixo (< 50ms) no redirecionamento.

---

## 9. Instruções para a próxima sessão
1. **Leitura obrigatória:** Ler `AGENTS.md` e este `docs/ESTADO_ATUAL.md` antes de qualquer ação.
2. **Estado do banco:** O banco `review_redirect` já possui a migração `0001_initial_schema` aplicada. Mantenha o container ativo via `docker compose up -d db`.
3. **Não alterar código existente sem necessidade:** As entidades em `app/models/` já estão validadas e não devem ser modificadas nesta etapa.
4. **Sem commits automáticos:** Aguardar orientações expressas do usuário antes de realizar commits.