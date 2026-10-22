# Estado Atual do Projeto ? Avalia??o Google

**Data da auditoria:** 22/10/2026 (Atualizado ao t?rmino da Fase 3)  
**Status do projeto:** Fases 1, 2 e 3 Conclu?das | Pronto para a Fase 4  
**Ambiente verificado:** Windows 10/11, Python 3.12.10, PostgreSQL 16.6 (Docker em localhost:5433), Git (branch `main`).

---

## 1. Vis?o Geral do Produto e da Arquitetura
- **Objetivo:** Plataforma de redirecionamento rastre?vel e inteligente para avalia??es no Google Meu Neg?cio / Google Maps via NFC e QR Code, voltada para lojistas e estabelecimentos comerciais f?sicos.
- **Fato fundamental de produto:** O redirecionamento rastreia o engajamento f?sico (aproxima??o por NFC ou leitura de QR Code), mas **n?o prova** a publica??o efetiva da avalia??o no Google. M?tricas de convers?o nunca devem ser fabricadas.
- **Stack t?cnica confirmada:**
  - Linguagem: Python 3.12.10
  - Framework Web: FastAPI 0.115.6 + Uvicorn 0.34.0 + Pydantic v2 (pydantic-settings 2.7.1)
  - Banco de Dados & ORM: PostgreSQL 16.6 + SQLAlchemy 2.0.36 + psycopg (v3) 3.2.4
  - Migra??es: Alembic 1.14.1
  - Testes: Pytest 8.3.4 (execu??o real contra PostgreSQL `review_redirect_test`)
  - Containeriza??o: Docker + Docker Compose (compose.yaml e compose.production.yaml)

---

## 2. Estrutura do Reposit?rio
```
Avaliacao Google/
??? app/
?   ??? __init__.py
?   ??? main.py                     # Inst?ncia FastAPI, healthcheck e rota de redirecionamento
?   ??? api/
?   ?   ??? __init__.py
?   ?   ??? health.py               # GET /health (liveness check)
?   ?   ??? redirect.py             # GET /r/{code} (redirecionamento p?blico 307 com Cache-Control: no-store)
?   ??? core/
?   ?   ??? __init__.py
?   ?   ??? config.py               # Settings pydantic-settings
?   ?   ??? database.py             # Engine lazy, Base declarativa, SessionLocal, get_db
?   ?   ??? tokens.py               # Gera??o segura de tokens n?o-sequenciais (secrets.token_urlsafe)
?   ??? models/
?   ?   ??? __init__.py             # Exporta todos os 6 modelos
?   ?   ??? user.py                 # Modelo User
?   ?   ??? business.py             # Modelo Business
?   ?   ??? business_membership.py  # Modelo BusinessMembership
?   ?   ??? review_link.py          # Modelo ReviewLink
?   ?   ??? access_event.py         # Modelo AccessEvent
?   ?   ??? review_snapshot.py      # Modelo ReviewSnapshot
?   ??? services/
?       ??? __init__.py
?       ??? url_validator.py        # Validador puro anti-open-redirect com allowlist oficial Google
?       ??? redirect_service.py     # Resolu??o de link, heur?stica de bot e registro de access_event
??? docs/
?   ??? ESTADO_ATUAL.md             # Este documento
??? migrations/
?   ??? env.py                      # Configura??o Alembic conectada ao app.core
?   ??? script.py.mako
?   ??? versions/
?       ??? 0001_initial_schema.py  # Migra??o inicial das 6 tabelas
??? tests/
?   ??? conftest.py                 # Fixtures Pytest (test_engine, db_session isolada com TRUNCATE, db_client)
?   ??? test_health.py              # Teste de rota /health
?   ??? test_models.py              # 14 testes de integridade relacional, constraints e cascade
?   ??? test_url_validator.py       # 57 testes rigorosos do validador anti-open-redirect
?   ??? test_redirect.py            # 15 testes de fluxo do endpoint p?blico GET /r/{code}
??? .env.example
??? AGENTS.md                       # Diretrizes permanentes para agentes de programa??o
??? alembic.ini
??? compose.yaml
??? compose.production.yaml
??? Dockerfile
??? README.md
??? requirements.txt
??? requirements-dev.txt
```

---

## 3. Estado das Funcionalidades

| Funcionalidade | Estado | Detalhes |
|---|---|---|
| Healthcheck (`GET /health`) | Conclu?do | Retorna `{"status": "ok"}` sem tocar no banco de dados. |
| Modelo de Dados Relacional | Conclu?do | 6 entidades SQLAlchemy 2.x com tipagem estrita `Mapped[...]` e constraints. |
| Migra??o Inicial Alembic | Conclu?do | Revis?o `0001_initial_schema` sincronizada com desenvolvimento e testes. |
| Validador Anti-Open Redirect | Conclu?do | Fun??o pura `validate_destination_url()` com allowlist estrita do Google. |
| Redirecionamento P?blico (`GET /r/{code}`) | Conclu?do | HTTP 307 com Location exato, `Cache-Control: no-store` e auditoria. |
| Registro de Eventos (`access_events`) | Conclu?do | Auditoria na mesma sess?o sem dados pessoais (sem IP, sem UA bruto). |
| Detec??o Heur?stica de Bots | Conclu?do | `is_probable_bot` (True/False/None) via substrings sem reter cabe?alhos. |
| Autentica??o & Autoriza??o | N?o iniciado | Previsto para a Fase 4 (decis?o de Sess?o vs JWT pendente de alinhamento). |
| Gest?o de Lojas e Links | N?o iniciado | Previsto para a Fase 4/5. |
| Painel e M?tricas | N?o iniciado | Previsto para a Fase 5. |
| Gera??o QR Code / NFC | N?o iniciado | Previsto para a Fase 6. |
| Rate Limiting | N?o iniciado | Risco mapeado para tratamento na Fase 7. |

---

## 4. Seguran?a e Validador de URLs (Fase 3)

### Fonte Oficial da Allowlist
A lista de dom?nios permitidos foi confirmada na documenta??o oficial do Google:
- **Fonte:** [Ajuda do Perfil da Empresa no Google ? Criar um link ou QR code para pedir avalia??es](https://support.google.com/business/answer/16816815?hl=pt-BR)

### Hostnames e Regras da Allowlist (`app/services/url_validator.py`)
- `g.page`: links curtos oficiais do Google Meu Neg?cio.
- `search.google.com`: permitido estritamente com path iniciando em `/local/writereview`.
- `maps.app.goo.gl`: links curtos gerados pelo aplicativo m?vel Google Maps.
- `www.google.com` e `google.com`: permitidos estritamente com path iniciando em `/maps`.
- `goo.gl`: permitido estritamente com path iniciando em `/maps`.

### Vetores Bloqueados pelo Validador
- Esquemas n?o-HTTPS (HTTP, FTP, javascript, data, protocol-relative `//`).
- Portas n?o-padr?o (rejeita qualquer porta diferente de 443).
- Userinfo / credenciais (`user:password@host` ou `g.page@evil.com`).
- Caracteres de controle ASCII (< 32, 127), whitespaces n?o tratados e backslashes (`\`).
- Duplo encoding (`%25`, `%5c`, etc.).
- Endere?os IP literais (IPv4 e IPv6).
- Hom?grafos Unicode e dom?nios punycode (`xn--...`).
- Subdom?nios n?o autorizados (ex.: `google.com.evil.com` ou `sub.g.page`).
- URLs maiores que 2048 caracteres.
- Execu??o puramente est?tica e determin?stica: nenhuma requisi??o de rede ou DNS ? realizada.

---

## 5. Testes Automatizados

- **Comando executado:**
  ```powershell
  .\.venv\Scripts\python -m pytest -v
  ```
- **Resultado consolidado:**
  - **87 testes aprovados, 0 falhos** em 2.16s contra PostgreSQL real (`review_redirect_test`).
  - Cobertura:
    - `tests/test_health.py`: 1 teste de liveness.
    - `tests/test_models.py`: 14 testes de constraints, integridade referencial, cascades e tokens.
    - `tests/test_url_validator.py`: 57 testes parametrizados (13 v?lidos, 44 vetores de ataque/malforma??o).
    - `tests/test_redirect.py`: 15 testes de fluxo HTTP (ativo 307, inativo 410, inexistente 404, malformado 404, destino fora da allowlist 502, heur?stica de bot, inspe??o de privacidade de colunas, acessos m?ltiplos consecutivos).

- **Verifica??o Alembic:**
  ```powershell
  .\.venv\Scripts\alembic check
  ```
  - Status: `No new upgrade operations detected.` (schema de banco perfeitamente alinhado com os modelos).

- **Medi??o de Desempenho Informative:**
  - Lat?ncia m?dia do endpoint `/r/{code}`: ~11.89 ms (incluindo consulta no banco e commit do `access_event`).

---

## 6. Riscos Mapeados

1. **Aus?ncia de Rate Limiting (Fase 3):**
   - O endpoint p?blico `GET /r/{code}` atualmente n?o possui limita??o de taxa por IP ou por c?digo de link.
   - *Mitiga??o planejada:* Implementa??o de rate limiting (ex.: SlowAPI / Redis ou token bucket em mem?ria) na Fase 7.
2. **Links com Destino Inv?lido n?o Geram Evento:**
   - Se um link tiver um destino que passe pelo `CheckConstraint` do banco (`LIKE 'https://%'`), mas seja rejeitado pelo validador da aplica??o (ex.: `https://evil.example`), o sistema responde 502 e n?o grava evento.
   - *Motivo t?cnico:* O banco possui `CheckConstraint("result IN ('redirected', 'blocked_inactive')")`. Gravar um resultado como 'blocked_invalid_url' exigiria nova migra??o de banco, o que estava explicitamente fora do escopo da Fase 3.
3. **Contagem de Acessos Inclui Bots:**
   - Requisi??es feitas por crawlers e bots gravam `access_event`, por?m com a coluna `is_probable_bot = True`.
   - *Aten??o para as Fases 5 e 6:* Os relat?rios e m?tricas do lojista dever?o filtrar explicitamente `is_probable_bot is not True` para evitar inflar artificialmente as visualiza??es f?sicas.

---

## 7. Pr?xima Tarefa Recomendada: Fase 4 (Autentica??o e Sess?o)

- **Pr?-requisito obrigat?rio:**
  - Confirmar com o usu?rio a estrat?gia de autentica??o antes de escrever c?digo:
    - **Op??o A:** Sess?o Stateful em Cookies HTTP-only (mais simples para pain?is web monol?ticos/SSR).
    - **Op??o B:** JWT Stateless com Bearer Token (ideal para APIs desacopladas e SPAs).
- **Escopo da Fase 4:**
  - Registro e login de usu?rios lojistas (`/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`).
  - Hashing seguro de senhas com `argon2-cffi` ou `bcrypt`.
  - Depend?ncias de inje??o `get_current_user` e `require_business_membership`.
