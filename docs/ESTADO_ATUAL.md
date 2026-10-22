# Estado Atual do Projeto — Avaliação Google

---

## 1. Última Auditoria
- **Data e Hora Local:** 22/10/2026 18:07 (Horário de Brasília)
- **Branch Ativa:** `main`
- **Último Commit (HEAD):** `0dac667 feat(redirect): adiciona GET /r/{code} e validador anti-open-redirect (Fase 3)`
- **Git Status:** Alterações de trabalho da Fase 4a presentes localmente, sem commit (conforme diretriz).
- **Limitações do Ambiente:**
  - PostgreSQL de desenvolvimento rodando via Docker em porta mapeada no host: `5433` (`DB_HOST_PORT=5433`).
  - Execução e testes realizados estritamente com `.venv` local e bancos `review_redirect` (dev) e `review_redirect_test` (testes).

---

## 2. Fase Atual
**Fase 4a Concluída — Autenticação de Lojistas e Administradores (Sessão por Cookie HttpOnly).**  
Pronto para a **Fase 4b** (Autorização por Loja e Gestão de Links/Estabelecimentos).

---

## 3. Estado das Funcionalidades

| Funcionalidade | Estado | Evidência / Arquivos |
|---|---|---|
| Liveness Check (`GET /health`) | Concluído | `app/api/health.py`, teste em `tests/test_health.py` |
| Modelo de Dados Relacional Base (6 tabelas) | Concluído | `app/models/` (user, business, membership, link, event, snapshot), migração `0001_initial_schema.py` |
| Validador Anti-Open Redirect | Concluído | `app/services/url_validator.py`, 57 testes em `tests/test_url_validator.py`. Allowlist oficial: `g.page`, `search.google.com/local/writereview`, `maps.app.goo.gl`, `www.google.com/maps`, `google.com/maps`. (`goo.gl` removido por não constar na doc oficial). |
| Redirecionamento Público (`GET /r/{code}`) | Concluído | `app/api/redirect.py`, 307 + Location + `Cache-Control: no-store`, 15 testes em `tests/test_redirect.py` |
| Auditoria Resiliente & Anônima de Acessos | Concluído | `app/services/redirect_service.py`, modelo `access_events` sem campos de IP ou User-Agent bruto |
| Detecção Heurística de Bots | Concluído | `detect_probable_bot` em `app/services/redirect_service.py`, flag `is_probable_bot` (True/False/None) |
| Modelo e Tabela de Sessões (`user_sessions`) | Concluído | `app/models/user_session.py`, migração `0002_add_user_sessions_table.py` |
| Hashing de Senhas (Argon2id) | Concluído | `app/core/security.py` via `argon2-cffi==25.1.0`, testes em `tests/test_security.py` |
| Login com Cookie HttpOnly (`POST /auth/login`) | Concluído | `app/api/auth.py`, emite cookie com `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` configurável |
| Proteção contra Timing Attacks no Login | Concluído | `authenticate_user` em `app/services/auth_service.py` (executa verificação contra hash fictício para usuários inexistentes) |
| Limitador de Tentativas de Login | Concluído | `app/services/login_rate_limiter.py` (bloqueio 429 após 5 falhas por 15 min, contador em memória) |
| Logout e Revogação (`POST /auth/logout`) | Concluído | `app/api/auth.py`, revoga sessão no banco e limpa cookie (204 No Content, idempotente) |
| Dados do Usuário Autenticado (`GET /auth/me`) | Concluído | `app/api/auth.py`, dependência `get_current_user` em `app/api/deps.py` |
| Proteção CSRF por Origem | Concluído | `_verify_csrf_origin` em `app/api/auth.py` validando headers `Origin`/`Referer` contra `ALLOWED_ORIGINS` |
| CLI de Criação de Administrador | Concluído | `app/cli.py` (`python -m app.cli create-admin --email EMAIL`), senha via getpass com confirmação e política (>=12 chars), testes em `tests/test_cli.py` |
| Autorização por Loja (`business_memberships`) | Não iniciado | Previsto para a Fase 4b |
| CRUD de Lojas e Links | Não iniciado | Previsto para a Fase 4b |
| Painel e Métricas | Não iniciado | Previsto para a Fase 5 |
| Geração de QR Code / NFC | Não iniciado | Previsto para a Fase 6 |
| Rate Limiting Global Distribuído | Não iniciado | Previsto para a Fase 7 |

---

## 4. Banco de Dados e Infraestrutura
- **PostgreSQL 16.6 (Docker):**
  - Banco de desenvolvimento: `review_redirect` em porta `5433` (migrações aplicadas até `0002_add_user_sessions`).
  - Banco de testes: `review_redirect_test` em porta `5433` (isolado, truncado a cada teste).
- **Tabelas Operacionais (7 entidades):**
  - `users`: id, email (único, lowercase forçado por CheckConstraint), password_hash (Argon2id), is_active, is_admin, timestamps.
  - `user_sessions`: id, user_id (FK cascade), token_hash (String(64) SHA-256 hex, unique), created_at, expires_at, revoked_at.
  - `businesses`: id, name, slug (único), google_review_url, timezone, is_active, timestamps.
  - `business_memberships`: id, user_id (FK cascade), business_id (FK cascade), role ('owner'/'manager'), created_at.
  - `review_links`: id, business_id (FK restrict), code (único), source ('nfc'/'qr'/'other'), label, destination_url, is_active, timestamps, deactivated_at.
  - `access_events`: id, review_link_id (FK restrict), occurred_at, result ('redirected'/'blocked_inactive'), is_probable_bot.
  - `review_snapshots`: id, business_id (FK restrict), captured_at, total_reviews, average_rating, source, status, error_message.
- **Ciclo de Migrações Testado:**
  - No banco `_test`: `0001 -> 0002` (upgrade head) -> `0001 -> base` (downgrade base) -> `0001 -> 0002` (upgrade head).
  - No banco de desenvolvimento: `alembic upgrade head` executado após validação total; `alembic check` reportando zero diferenças.

---

## 5. Testes Automatizados

- **Comando executado:**
  ```powershell
  .\.venv\Scripts\python -m pytest -v
  ```
- **Resultado consolidado:**
  - **104 testes aprovados, 0 falhos** em 4.66s contra PostgreSQL real (`review_redirect_test`).
  - Distribuição:
    - `tests/test_health.py`: 1 teste
    - `tests/test_models.py`: 14 testes
    - `tests/test_url_validator.py`: 57 testes (incluindo rejeição de `goo.gl`)
    - `tests/test_redirect.py`: 15 testes
    - `tests/test_security.py`: 4 testes (política de senha, hashing Argon2, token e SHA-256)
    - `tests/test_auth.py`: 8 testes (login, logout, me, cookies, timing attack, CSRF e require_admin)
    - `tests/test_cli.py`: 5 testes (criação de admin, política, senhas divergentes, duplicidade)

- **Alembic Check:**
  ```powershell
  .\.venv\Scripts\alembic check
  ```
  - Status: `No new upgrade operations detected.`

---

## 6. Segurança e Política de Credenciais

1. **Hashing de Senhas (Argon2id):**
   - Utiliza a biblioteca `argon2-cffi==25.1.0` com parâmetros padrão recomendados (RFC 9106).
   - Verificação em tempo constante mitigada por hash fictício (`DUMMY_PASSWORD_HASH`) quando o usuário não é encontrado.
2. **Tokens de Sessão Server-side:**
   - Token gerado via `secrets.token_urlsafe(32)`.
   - O banco de dados armazena **estritamente o hash SHA-256 (hex de 64 caracteres)** do token (`token_hash`), impedindo vazamento de sessões em caso de dump do banco.
   - O token em claro só transita no cookie `session_id`.
3. **Segurança do Cookie:**
   - `HttpOnly`: impede acesso ao token via scripts maliciosos (XSS).
   - `SameSite=Lax`: protege contra requisições cross-site não seguras em navegação externa.
   - `Path=/`: restringe ao escopo completo da aplicação.
   - `Secure`: controlado por variável de ambiente (`COOKIE_SECURE`, padrão `true` em produção).
   - `Cache-Control: no-store` aplicado em todas as respostas de autenticação.
4. **Proteção Adicional contra CSRF:**
   - Verificação de cabeçalhos `Origin` e `Referer` contra `ALLOWED_ORIGINS` em métodos não-seguros (POST).
5. **Mitigação de Brute Force (Login Rate Limiter):**
   - Contador em memória por email normalizado (máximo 5 falhas / janela de 15 minutos). Retorna HTTP 429 Too Many Requests com cabeçalho `Retry-After`.
6. **Allowlist Anti-Open Redirect Atualizada:**
   - O domínio `goo.gl` foi **removido** da allowlist oficial por não constar na documentação oficial atual do Perfil da Empresa no Google ([Google Business Answer 16816815](https://support.google.com/business/answer/16816815?hl=pt-BR)).
   - Domínios autorizados mantidos: `g.page`, `search.google.com` (prefixo `/local/writereview`), `maps.app.goo.gl`, `www.google.com` (prefixo `/maps`), e `google.com` (prefixo `/maps`).

---

## 7. Pendências Priorizadas

### P0 — Bloqueadores Críticos
- *Nenhum bloqueador crítico.* Autenticação e redirecionamento validados e integrados.

### P1 — Necessários para a Próxima Etapa (Fase 4b)
1. **Autorização por Estabelecimento:**
   - Injeção de dependência `require_business_membership` para isolar acesso de lojistas a estabelecimentos específicos (`business_memberships.role in ('owner', 'manager')`).
2. **CRUD de Lojas e Links:**
   - Endpoints para criação e listagem de estabelecimentos (`/businesses`) e review_links (`/businesses/{id}/links`).

### P2 — Melhorias Posteriores (Fases 5 a 7)
1. Painel de métricas e relatórios agregados sem computar bots (Fase 5).
2. Geração de imagens QR Code e payloads NFC (Fase 6).
3. Rate limiting distribuído global via Redis / SlowAPI (Fase 7).
4. Fluxos de recuperação de senha e MFA (fora do escopo das fases 1-4).

---

## 8. Próxima Tarefa Recomendada
- **Fase 4b — Autorização por Loja e CRUD de Links e Estabelecimentos:**
  - Implementar dependências de controle de acesso multi-tenant com base em `business_memberships`.
  - Implementar endpoints para lojistas gerenciarem suas lojas e gerarem novos links (`source='nfc'|'qr'`).
  - Utilizar o validador `validate_destination_url` no cadastro de novos links de avaliação.

---

## 9. Instruções para a Próxima Sessão
1. **Leitura Obrigatória:** Ler `AGENTS.md` e este documento `docs/ESTADO_ATUAL.md` antes de qualquer alteração.
2. **Preservar Trabalho:** Não commitar nem reverter alterações sem instrução expressa do usuário.
3. **Ambiente de Testes:** Manter execução de testes sempre contra `_test` (`review_redirect_test`).
4. **Encoding UTF-8:** Todas as alterações devem ser gravadas estritamente em UTF-8 sem corrupção de caracteres.
