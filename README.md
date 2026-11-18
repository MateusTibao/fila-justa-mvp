# Fila Justa — Ficha Técnica do MVP

**Nome:** Fila Justa | **Área:** gestão urbana e priorização territorial | **Cidade inicial:** São Paulo (SP).

**Problema:** demandas urbanas excedem a capacidade de atendimento. **Proposta:** oferecer uma fila de priorização justa, explicável e sensível ao clima e um fluxo separado de gestão das ocorrências selecionadas.

## Arquitetura

- **Big Data:** pipeline Airflow e PostgreSQL com camadas Bronze, Silver e Gold. Snapshot `gold` disponível para consulta no Azure.
- **Camada pública:** aplicativo Flask lê `gold.mart_fila_priorizacao` com usuário `app_reader` somente leitura; exibe todas as ocorrências agrupadas da fotografia atual, com busca e paginação, sem login.
- **Camada operacional (Fila Justa):** schema PostgreSQL `operacional`, autenticação de usuários, atualização de acompanhamento com histórico de mudanças, vinculada ao `cluster_id` da Gold.
- **CI/CD:** GitHub Actions. A aprovação e a publicação em Azure são passos controlados após testes e migração.

**Fontes analíticas:** SP156, IBGE Censo 2022, Open-Meteo e relatos simulados. **ODS:** 9, 10, 11 e 13. **Natureza:** protótipo acadêmico, não oficial da Prefeitura.

## Funcionalidades

A consulta pública não exige login nem schema operacional. A gestão operacional é habilitada **somente** quando os dois valores `OPERATIONAL_DATABASE_URL` e `FJ_SESSION_SECRET` estão configurados, e após executar as migrações em um banco de testes:

| Tela | Função |
|---|---|
| `/login` | Autenticação de operador, gestor ou administrador |
| `/gestao/demandas` | Lista de demandas com busca, filtro e paginação |
| `/gestao/kanban` | Entrada analítica automática e quadro de acompanhamento com histórico e movimentações |
| `/gestao/dashboard` | Indicadores de gestão com gráficos de etapas, distribuição territorial, categorias e movimentos recentes |
| `/` | Observatório público: KPIs, gráficos de tipos, territórios e faixas de pontuação calculadas da Gold |
| `/ocorrencias` | **Todas as ocorrências da Gold**, com busca por ID, título, categoria ou distrito e paginação |
| `/ocorrencias/<cluster_id>` | Detalhe público, pontuação, explicação analítica e acompanhamento (quando existe) |
| `/api/ocorrencias` | Consulta JSON paginada, somente leitura, sem autenticação |
| `/gestao/kanban` | **Entrada automática da fila analítica**: gestor encaminha cartão existente, sem novo cadastro |
| `/gestao/dashboard` | Gráficos dos atendimentos registrados e movimentações reais dos últimos sete dias |

**Etapas operacionais:** recebida → em triagem → em atendimento → em conferência → concluída; também existe arquivada. A prioridade não é atribuída manualmente e não depende de prazo. Gestor/administrador validam conclusões. Cada mudança registra autor, horário, versão e justificativa. Alterações concorrentes retornam HTTP 409.

A consulta lê a **prioridade corrente** diretamente da Gold, sem gerar uma demanda operacional por ocorrência. Ao selecionar **Iniciar acompanhamento** em um cartão, o gestor cria o registro de acompanhamento uma única vez e o encaminha para triagem. Repetir essa ação não apaga histórico nem altera a etapa já registrada. O score armazenado no acompanhamento identifica a pontuação no momento da entrada; o catálogo público continua exibindo a pontuação corrente da Gold. O módulo GenAI está em repositório separado e **não foi acoplado** a esta alteração.

## Consulta pública e simulação

- A fila é alimentada pelo snapshot `gold.mart_fila_priorizacao` do pipeline SP156 + IBGE + clima + relatos simulados; o aplicativo **não coleta diretamente** esses sites em tempo real e não abre protocolo municipal.
- Cartões, posição e pontuação são gerados pela Gold, sem cadastro manual. O buscador aceita `cluster_id`, categoria, título construído de categoria/distrito e distrito. A paginação consulta a fonte sem trazer tudo para a página.
- A aba de simulação funciona **somente no navegador** e na sessão atual; não grava banco nem indica atendimento público efetivamente realizado.
- Na operação, apenas o gestor/autorizado registra o início do acompanhamento e a equipe atualiza etapas com auditoria. A ação `/api/gestao/acompanhar` exige login e CSRF.
- Gráficos públicos mostram a **fotografia atual** da Gold, e não uma série de evolução histórica. O gráfico diário de movimentações do painel de gestão é construído dos eventos realmente gravados.
- Status de atendimento e pontuação de prioridade são informações independentes; nunca deduzir atendimento concluído a partir do score.

**Datas operacionais:** a previsão de conclusão é informada e exibida em **dd/mm/aaaa**, sem horário. O dia inteiro é considerado, no fuso `America/Sao_Paulo`: se o prazo previsto é 17/11, o cartão só recebe a marcação **Prazo vencido** a partir de 18/11, desde que continue aberto. Ocorrências concluídas/arquivadas não são marcadas como vencidas. Os carimbos de movimentação aparecem somente com a data na interface; os horários completos continuam preservados na auditoria.

[Contrato técnico da fila e da demonstração](docs/FLUXO_PUBLICO.md).

## Saúde e disponibilidade

- `GET /health`: retorna HTTP 200 quando o processo Flask está atendendo requisições, sem consultar o PostgreSQL.
- `GET /ready`: retorna HTTP 200 se a consulta de conectividade ao PostgreSQL funcionar; caso contrário, HTTP 503.
- O teste de disponibilidade do Application Insights utiliza `/ready`, não `/health`.
- A publicação Azure permanece **manual** e separada do CI; nenhum push atualiza automaticamente o site.
- As funcionalidades de gestão exigem `OPERATIONAL_DATABASE_URL` com permissões mínimas de escrita no schema `operacional`; o usuário `app_reader` continua somente leitura.

## Segurança da implantação Azure (Etapa 8)

**Status: EM CONFIRMAÇÃO, aguardando retorno do professor.** Os controles foram auditados: HTTPS/TLS, RBAC, FTP/FTPS desativado e papéis mínimos do PostgreSQL foram validados. A implantação F1 ainda depende da exceção de firewall `fj-f1-azure-acesso` (`0.0.0.0`, autorização para serviços Azure) para acessar o PostgreSQL. Isso **não é isolamento privado de rede** e não deve ser apresentado como configuração definitiva para produção. A continuidade acadêmica com essa limitação foi submetida ao professor, **sem resposta registrada até o momento**.

O motivo da pendência, os testes realizados, os riscos, as medidas compensatórias e os critérios para corrigi-la estão registrados em [Etapa 8 — Auditoria e pendência de rede](docs/ETAPA_8_SEGURANCA.md).

## Documentação da entrega Cloud (Etapa 12)

- [Arquitetura Cloud e evidências de validação](docs/ETAPA_12_ARQUITETURA_CLOUD.md)
- [Etapa 13 — Relatório final e roteiro de entrega](docs/ETAPA_13_RELATORIO_ENTREGA.md)
- [Etapa 8 — Segurança: EM CONFIRMAÇÃO do professor](docs/ETAPA_8_SEGURANCA.md)
- [CI/CD e autenticação OIDC](docs/CI_CD.md)
- [Etapa 13 — Relatório final e roteiro de entrega](docs/ETAPA_13_RELATORIO_ENTREGA.md)

A documentação da Etapa 12 consolida o pipeline Bronze/Silver/Gold validado no ambiente de engenharia, o snapshot Gold e o schema operacional na Azure, o fluxo de implantação e as pendências das etapas 8, 10, 11 e 13. O processamento Airflow **não foi declarado implantado continuamente na Azure**.

## Configurar localmente (antes de Azure)

Python 3.12 recomendado. Em Git Bash no Windows:

```bash
py -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Configure a leitura Gold como anteriormente (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` e, opcionalmente, `DB_PORT`). O servidor exige conexão SSL.

Para ativar a operação, **não use** `app_reader` como identidade de escrita. No PostgreSQL de testes, com conta administradora de migração e backup feito:

```bash
psql "$OPERATIONAL_MIGRATION_DATABASE_URL" -X -v ON_ERROR_STOP=1 -f migrations/001_operacional.sql
psql "$OPERATIONAL_MIGRATION_DATABASE_URL" -X -v ON_ERROR_STOP=1 -f migrations/002_usuarios.sql
```

Crie um usuário PostgreSQL novo para o app, com os grants mínimos em SQL (executar como admin, depois da criação do papel):

```sql
GRANT USAGE ON SCHEMA operacional TO app_operador;
GRANT SELECT, INSERT, UPDATE ON operacional.demandas TO app_operador;
GRANT SELECT, INSERT ON operacional.historico_status TO app_operador;
GRANT SELECT ON operacional.usuarios TO app_operador;
GRANT USAGE ON SCHEMA gold TO app_operador;
GRANT SELECT ON gold.mart_fila_priorizacao TO app_operador;
```

Configure localmente, **fora do Git**:

- `OPERATIONAL_DATABASE_URL`: `postgresql+psycopg://app_operador:<SENHA>@<HOST>:5432/<BANCO>?sslmode=require`.
- `FJ_SESSION_SECRET`: valor aleatório com pelo menos 32 caracteres, diferente das credenciais do banco.
- `OPERATIONAL_MIGRATION_DATABASE_URL`: conexão temporária de provisionamento, não configurar no Azure App Service.
- `FJ_LOCAL_HTTP=1`: somente para desenvolvimento em `http://localhost`; **não configurar em produção**, onde cookies de sessão exigem HTTPS.

Crie a primeira conta com uma senha forte solicitada interativamente, sem guardar no terminal nem no Git:

```bash
python -m fj_operacional.admin --email gestor@exemplo.org --nome "Gestor de teste" --perfil gestor
flask --app app run
```

**Importante:** a identidade de provisionamento exige INSERT/UPDATE em `operacional.usuarios`. O usuário do site em execução tem apenas SELECT nessa tabela. Nunca usar a identidade de migração no servidor web.

## Verificação antes de publicar

1. Testes unitários, HTTP e de regressão aprovados.
2. PostgreSQL de testes com as duas migrações aplicadas; `app_operador` não altera a Gold.
3. Login, logout, bloqueio de convidados e CSRF verificados.
4. Gestor cria/importa, operador executa, gestor conclui, histórico e HTTP 409 conferidos.
5. Filtragem, paginação, dashboard e Kanban operando com dados reais de teste.
6. Avaliar CI e deploy Azure separadamente, sem publicar automaticamente enquanto houver teste vermelho.

**Limitações:** perfis internos são provisionados por CLI; não há cadastro aberto, notificações ou upload de anexos. O protótipo não inclui integração efetiva ao repositório GenAI e não se apresenta como serviço oficial.
