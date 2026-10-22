# Estado Atual do Projeto — Avaliação Google

## 1. Última Auditoria

- Data: 22/10/2026.
- Branch: `main`; alterações locais não commitadas.
- Evidência: `git status -s` após a implementação lista apenas arquivos da Fase 4b e documentação; nenhum arquivo de migração foi alterado.

## 2. Fase Atual

Fase 4b concluída: autorização por loja, CRUD privado de lojas/links, correções da 4a e CLI adicional. A Fase 5 não foi iniciada.

## 3. Funcionalidades

- Autenticação por sessão, CSRF Origin/Referer e cookies configuráveis: concluído.
- Autorização por `business_memberships`: admin vê tudo; owner, manager e isolamento 404 implementados.
- CRUD de lojas e links em `/api/*`, paginação, validação de timezone/URL/slug e `PUBLIC_BASE_URL`: concluído.
- Link imutável em `code`, `source` e `destination_url`; loja inativa não redireciona e gera `blocked_inactive`: concluído.
- Allowlist atual não foi alterada. Hostnames nela: `g.page`, `search.google.com`, `maps.app.goo.gl`, `www.google.com` e `google.com`.
- Evidência: `pytest -v` — 107 passed; `alembic check` — `No new upgrade operations detected.`

## 4. Banco e Migrações

Modelos e migrações 0001/0002 foram preservados. Nenhuma migração nova foi necessária. Evidência: `.venv\Scripts\alembic.exe check` sem diferenças.

## 5. Testes Automatizados

- Comando: `.venv\Scripts\python.exe -m pytest -v`.
- Resultado: 107 aprovados, 0 falhos, 1 warning de depreciação do Starlette.
- O banco usado foi o banco `_test`; os testes cobrem isolamento básico, papéis, link inativo, imutabilidade e admin.

## 6. Segurança e Privacidade

- Respostas `/api/*` usam `Cache-Control: no-store`; respostas não expõem hashes.
- Limitador de login é em memória por processo, configurado por settings, com teto de 10.000 chaves e lockout por email.
- CSRF usa Origin/Referer mais `SameSite=Lax`; não há MFA, recuperação de senha ou rate limiting global.
- Não há review gating nem automação de avaliações.

## 7. Riscos e Pontos de Atenção

- O limitador em memória não é distribuído entre workers.
- O lockout por email pode exigir estratégia adicional contra abuso em escala.
- A página oficial consultada (`https://support.google.com/business/answer/16816815?hl=pt-BR`) explica a criação/compartilhamento de links e QR codes, mas não lista hostnames explicitamente no conteúdo obtido; portanto os hostnames da allowlist permanecem não verificados na documentação, incluindo `maps.app.goo.gl`.
- Não foram alterados modelos, Docker, Compose ou migrações.

## 8. Decisões Provisórias desta Fase

- Usuário sem membership recebe 404 para não revelar existência de loja/link.
- Admin possui papel efetivo `admin`; manager não edita loja; owner pode editar; links desativados podem ser reativados.
- `PUBLIC_BASE_URL` é opcional e `public_url` só é emitido quando configurado.
- CLI nunca recebe senha por argumento.

## 9. Próxima Tarefa

Próxima tarefa recomendada: Fase 5 (M5.0) ou auditoria dos pontos A1–A12 conforme `FASE_5_INTERFACE_ADMINISTRATIVA.md`, sem iniciar essa fase nesta entrega.
