# Diretrizes para Agentes de Programação (AGENTS.md)

Este documento estabelece as instruções e convenções permanentes para todos os agentes de IA de programação (Antigravity/Gemini, Claude Code, OpenAI Codex, Cursor, etc.) que atuarem no repositório **Avaliação Google**.

---

## 1. Contexto do Produto
- **Objetivo:** Plataforma de redirecionamento rápido e rastreável para acesso a avaliações do Google Meu Negócio via cartões físicos NFC e adesivos/placas com QR Code.
- **Público-alvo:** Lojistas e estabelecimentos comerciais que desejam incentivar avaliações legítimas no Google e acompanhar o engajamento dos clientes.
- **Funcionalidades principais do sistema:**
  - Redirecionamento veloz via rotas curtas (ex.: `/r/{code}`) para a página de avaliação do estabelecimento no Google.
  - Rastreabilidade de acessos por identificador de dispositivo/ponto físico (tags NFC ou QR Codes específicos por mesa, caixa, atendente ou unidade).
  - Painel de métricas e relatórios para os lojistas (contagem de cliques, horários de pico, comparativo de pontos físicos).

---

## 2. Stack Técnica e Padrões Arquiteturais
Respeite estritamente a stack e as versões fixadas no repositório:
- **Linguagem:** Python 3.12 (base container: `python:3.12.8-slim`).
- **Framework Web:** FastAPI (0.115.6) com servidor ASGI Uvicorn (0.34.0).
- **Validação e Configurações:** Pydantic / `pydantic-settings` (2.7.0) com leitura de variáveis via `BaseSettings` (`app/core/config.py`).
- **Banco de Dados:** PostgreSQL 16 (imagem container: `postgres:16.6-alpine`).
- **ORM e Conexão:** SQLAlchemy 2.0.36 utilizando sintaxe declarativa 2.x (`DeclarativeBase`), engine em `app/core/database.py` com driver `psycopg` v3 (`postgresql+psycopg://`).
- **Migrações:** Alembic (1.14.0) configurado em `alembic.ini` e `migrations/env.py` (resolvendo a URL dinamicamente via `get_settings().database_url`).
- **Testes Automatizados:** Pytest (8.3.4) e HTTPX (0.28.1).
- **Containerização:** Docker e Docker Compose (especificação moderna Compose com `compose.yaml` e override `compose.production.yaml`).

### Organização de Diretórios
- `app/api/`: Rotas e endpoints HTTP (FastAPI `APIRouter`).
- `app/core/`: Configurações (`config.py`), conexão de banco (`database.py`) e segurança/constantes.
- `app/models/`: Modelos declarativos SQLAlchemy 2.x.
- `app/schemas/`: Esquemas de validação e serialização Pydantic.
- `app/services/`: Lógica de negócio e regras operacionais desacopladas dos controllers.
- `migrations/`: Scripts de migração do schema do banco via Alembic.
- `tests/`: Testes automatizados unitários e de integração (`conftest.py` com fixtures).

---

## 3. Inspeção Prévia Obrigatória
Antes de propor ou realizar qualquer modificação no código:
1. **Inspecione os arquivos existentes:** Leia e compreenda a arquitetura atual, estilos de codificação e padrões de nomenclatura.
2. **Verifique o estado do controle de versão:** Execute `git status` e `git diff` para entender mudanças pendentes ou arquivos não rastreados.
3. **Não presuma caminhos ou dependências:** Verifique se as bibliotecas necessárias já constam em `requirements.txt` / `requirements-dev.txt` antes de tentar importá-las ou instalá-las.

---

## 4. Execução por Tarefas e Escopo Estrito
- **Foco Cirúrgico:** Implemente estritamente o que foi solicitado pelo usuário no escopo da tarefa atual.
- **Passos Incrementais:** Prefira mudanças pequenas, coesas e fáceis de validar.
- **Não Refatore Sem Pedido:** Não realize refatorações amplas, renomeações em massa ou reorganizações estruturais sem autorização expressa.
- **Sem Funcionalidades Não Solicitadas:** Não adicione funcionalidades fora do escopo imediato (ex.: SDKs externos, telas extras, bibliotecas de terceiros desnecessárias).

---

## 5. Banco de Dados e Integridade do Schema
- **Schema Controlado:** Toda e qualquer alteração de schema deve ser obrigatoriamente realizada por meio de migrações versionadas do Alembic (`migrations/versions/`).
- **Revisão Manual de Migrações:** Migrações geradas automaticamente devem ser inspecionadas linha por linha para garantir que operações como `ALTER COLUMN`, `DROP TABLE` ou índices sejam seguras e idempotentes.
- **Startup Limpo:** Nunca execute migrações de banco automaticamente no início do container de aplicação (`app`). A execução deve ser explícita via comando administrativo (`alembic upgrade head`).
- **Preservação de Dados:** Nunca execute comandos destrutivos (`DROP DATABASE`, `TRUNCATE`, exclusões em massa sem filtro `WHERE`) e não altere dados reais sem consentimento do usuário.

---

## 6. Segurança e Isolamento
- **Segredos e Credenciais:** Nunca versione ou insira senhas, chaves de API, credenciais ou strings de conexão com credenciais reais em arquivos rastreados pelo Git, Dockerfiles ou testes. Utilize sempre variáveis de ambiente e o arquivo `.env` (ignorado no `.gitignore`).
- **Prevenção de Open Redirect:** O endpoint de redirecionamento (`/r/{code}`) deve validar rigorosamente o destino final. O sistema deve impedir que URLs externas maliciosas, esquemas não seguros (`javascript:`, `data:`) ou domínios estranhos ao Google Meu Negócio sejam aceitos como destino.
- **Validação de Entrada:** Todas as entradas de dados devem ser tipadas e validadas através de schemas Pydantic.
- **Multi-tenant e Autorização:** O painel de métricas e os dados de estabelecimentos devem possuir controle de acesso rigoroso no backend, garantindo que nenhum lojista visualize ou modifique dados de outras empresas ou lojas.

---

## 7. Privacidade e Diretrizes do Google
- **Coleta Mínima de Dados:** Colete apenas as informações necessárias para medição e auditoria (ex.: timestamp do clique, identificador do link, User-Agent para detecção de dispositivo/bot, e endereço IP com técnicas de anonimização ou hashing conforme LGPD).
- **Proibição de Review Gating:** Em conformidade com as políticas do Google e órgãos de defesa do consumidor, o sistema **NUNCA** deve implementar práticas de *review gating* (filtrar clientes satisfeitos para o Google e insatisfeitos para canais internos). Todos os clientes devem ter acesso neutro e transparente ao link de avaliação.
- **Sem Automação ou Fabricação de Avaliações:** O sistema não deve tentar automatizar a publicação de textos ou notas na plataforma do Google, nem simular avaliações de clientes. A avaliação deve ser redigida e enviada voluntariamente pelo usuário logado no Google.
- **Sem Falsas Promessas:** O sistema deve deixar claro para o lojista que a métrica registrada representa o **acesso/toque ao link** e não uma confirmação de que a avaliação foi efetivamente postada pelo cliente (o Google não fornece essa confirmação sem OAuth individual do cliente).

---

## 8. Testes Automatizados
- **Desacoplamento:** Os testes unitários e de rotas básicas não devem depender da infraestrutura do PostgreSQL estar em execução. Use configurações em memória, mocks ou transações isoladas conforme padronizado no `tests/conftest.py`.
- **Cobertura Obrigatória:** Todo novo endpoint, serviço de validação ou regra de redirecionamento deve acompanhar seu teste automatizado.
- **Execução Real:** Ao concluir uma alteração, execute a suíte de testes (`pytest`) no ambiente local ou container e informe os comandos utilizados.
- **Clareza de Status:** Relate com transparência os testes aprovados, testes reprovados e testes que não puderam ser executados.

---

## 9. Transparência e Integridade
- **Veracidade dos Relatos:** Nunca invente resultados de testes, afirmações de sucesso em builds não executados, supostas aprovações de APIs de terceiros ou credenciais fictícias.
- **Problemas Conhecidos:** Se um comando falhar ou houver um erro de ambiente (ex.: porta ocupada, serviço parado), relate o erro exato e a solução adotada.

---

## 10. Conclusão e Entrega de Tarefas
Ao finalizar qualquer tarefa ou sprint, o agente deve fornecer um sumário estruturado contendo:
1. **Resumo das alterações:** O que foi feito e por qual motivo técnico.
2. **Arquivos afetados:** Lista clara de arquivos criados, modificados ou removidos.
3. **Validação realizada:** Comandos exatos executados e seus respectivos resultados.
4. **Riscos e pontos de atenção:** Possíveis impactos em outras áreas da aplicação.
5. **Pendências e Próximos Passos:** O que ficou reservado para as fases subsequentes.

---

## 11. Preservação do Trabalho Existente
- **Proteção do Código do Usuário:** Nunca apague, limpe ou sobrescreva arquivos criados ou modificados pelo usuário sem confirmação explícita.
- **Reversões Indesejadas:** Nunca execute comandos destrutivos no Git (`git reset --hard`, `git checkout .`, `git clean -fd`) sem alinhamento e autorização expressa.

---

## 12. Documentação e Decisões Técnicas
- Mantenha o `README.md` e a documentação interna sempre sincronizados com o comportamento real do software.
- Registre decisões técnicas, hipóteses assumidas e itens provisórios no código (via docstrings/comentários) e na documentação.

---

## Decisões Provisórias do Repositório (A Confirmar com o Usuário)
As seguintes configurações foram adotadas como placeholders na fundação do projeto e podem ser alteradas futuramente conforme alinhamento de negócio:
- **Identificador e Nome do Projeto:** `review-redirect` (definido em `app/core/config.py` e `.env.example`).
- **Porta Local da API:** `8000` (mapeada no Compose e Uvicorn).
- **Porta Host do Banco de Dados (Dev):** `DB_HOST_PORT` com padrão `5432` e fallback para `5433` em caso de conflito com instâncias locais existentes de PostgreSQL.
- **Banco de Dados Padrão:** `review_redirect` com usuário `app_user`.
- **Estratégia de Redirecionamento Futura:** Formato `/r/{code}` para slugs curtos e códigos alfanuméricos gerados para os pontos de contato.