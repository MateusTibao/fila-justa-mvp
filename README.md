# Fila Justa — Ficha Técnica do MVP

**Nome:** Fila Justa | **Área:** gestão urbana e priorização territorial | **Cidade inicial:** São Paulo (SP).

**Problema:** demandas urbanas excedem a capacidade de atendimento. **Proposta:** oferecer uma fila de priorização justa, explicável e sensível ao clima e um fluxo separado de gestão das ocorrências selecionadas.

## Arquitetura

- **Big Data:** pipeline Airflow e PostgreSQL com camadas Bronze, Silver e Gold. Snapshot `gold` disponível para consulta no Azure.
- **Camada pública:** aplicativo Flask lê `gold.mart_fila_priorizacao` com usuário `app_reader` somente leitura; exibe todas as ocorrências agrupadas da fotografia atual, com busca e paginação, sem login.
- **Camada operacional (Fila Justa):** schema PostgreSQL `operacional`, autenticação de usuários, atualização de acompanhamento com histórico de mudanças, vinculada ao `cluster_id` da Gold.
- **CI/CD:** GitHub Actions. A aprovação e a publicação em Azure são passos controlados após testes e migração.

**Fontes analíticas:** SP156, IBGE Censo 2022, Open-Meteo e relatos simulados. **ODS:** 9, 10, 11 e 13. **Natureza:** protótipo acadêmico, não oficial da Prefeitura.

## Funcionalidades: duas áreas

O aplicativo apresenta **apenas duas opções principais de navegação**, sempre na mesma posição: **Público** e **Gestor**.

| Área | Página principal | O que faz |
|---|---|---|
| **Público** | `/` | Busca demandas por título ou ID, exibe pontuação calculada pela Gold, situação atual e detalhamento sem login |
| **Gestor** | `/gestao/kanban` | Mostra primeiro o Kanban dos acompanhamentos e, abaixo, as demandas recebidas para encaminhamento; registra mudanças de etapa ou justificativas mantendo a mesma etapa |

As URLs técnicas de `/login`, `/ocorrencias/<cluster_id>`, `/api/...`, `/health` e `/ready` continuam disponíveis para autenticação, detalhes, integração e monitoramento, mas **não aparecem como áreas adicionais no menu**. Os endereços antigos `/ocorrencias`, `/gestao/dashboard` e `/gestao/demandas` redirecionam para a página correspondente.

A consulta pública não exige login. A área do gestor só é habilitada com `OPERATIONAL_DATABASE_URL` e `FJ_SESSION_SECRET` configurados, após aplicar as migrações operacionais. O gestor não abre uma nova demanda manualmente, não edita a origem nem define a pontuação: o pipeline Bronze/Silver/Gold fornece os registros e o ranking.

Na primeira interação com uma demanda recebida, **Encaminhar para triagem** vincula a ocorrência à camada operacional de forma idempotente. A partir daí, o gestor/equipe podem atualizar o andamento. **Toda atualização pela interface exige justificativa, inclusive para registrar progresso sem trocar a etapa no Kanban**. Essa observação é armazenada no histórico (`tipo_evento=edicao`, sem troca de status), com autoria, horário e controle de versão. Alterações concorrentes retornam HTTP 409.

A mudança de estado respeita a sequência e as permissões já definidas no módulo operacional. Ações de criar demanda manual, importar por ID e editar seus dados não ficam mais disponíveis por rotas HTTP; permanecem funções internas/legadas de persistência. O formulário de prazo de conclusão foi retirado da interface do gestor; prazos já registrados continuam visíveis, com o aviso **Prazo vencido** conforme o calendário de São Paulo.

A interface pública mostra a situação persistida quando existe acompanhamento operacional, ou **Sem acompanhamento registrado** quando ainda não há atualização. Nenhuma simulação altera ou mascara esse estado. Os indicadores agregados permanecem disponíveis em uma seção expansível da página pública. O módulo GenAI continua separado e não foi integrado.

## Origem e limites

As ocorrências do protótipo são processadas pelo pipeline já existente, que combina fontes SP156, IBGE, clima e relatos simulados na base analítica. A descrição curta exibida na página pública menciona apenas SP156, conforme o texto de interface definido. Essa alteração editorial **não retira os dados simulados que possam estar presentes na Gold**.

A pontuação da Gold não constitui prazo de atendimento nem indicador de serviços concluídos. As datas aparecem como `dd/mm/aaaa`, mas os instantes completos permanecem no histórico do PostgreSQL.

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

1. Executar os testes Python, Flask e validação de sintaxe JavaScript no CI.
2. Confirmar `/` com busca, detalhamento e status público sem login.
3. Confirmar login/CSRF, Kanban primeiro, entrada de demandas embaixo, sem edição nem cadastro manual.
4. Validar atualização com nova etapa e atualização mantendo a etapa, ambas com justificativa.
5. Validar histórico, controle de versão (HTTP 409), restrições de perfil e prazo vencido.
6. Executar o deploy Azure **manualmente**, após o CI verde e a verificação das conexões.

**Limitações:** protótipo acadêmico não oficial, sem integração de GenAI e com atualização de dados limitada à última execução do pipeline.
