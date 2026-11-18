# Fila Justa — entrada analítica, acompanhamento e demonstração

## Fontes e limites

O pipeline existente coleta dados SP156, IBGE, meteorologia e relatos simulados,
os padroniza em Bronze/Silver e publica priorização e agrupamentos no schema Gold.
A aplicação Flask **consulta a fotografia atual** de
`gold.mart_fila_priorizacao`; não abre protocolo na Prefeitura e não coleta
novos incidentes diretamente dos sites. O ano e cobertura são os da última
rodada publicada, que pode ser parcial.

## Novo fluxo

1. O pipeline recalcula `rank`, `cluster_id`, `tipo`, `area_nome`,
   `n_relatos`, `score_0_100`, `explicacao` e `run_id`.
2. `/` exibe indicadores agregados e cartões prioritários.
3. `/ocorrencias` e `/api/ocorrencias` consultam todas as posições
   **com paginação de até 30 itens por consulta**, sem login.
   Busca por ID do cluster, categoria ou distrito, inclusive a combinação
   usada para construir o título do cartão.
4. A pontuação vem sempre da Gold e é apresentada na escala de 0 a 100,
   não como probabilidade de atendimento e não como prazo.
   As faixas elevadas (>=75), intermediárias (>=50) e de monitoramento
   (<50) são **faixas ilustrativas de visualização** e não classificação oficial.
5. A tela de gestão traz uma projeção das primeiras ocorrências ainda sem
   acompanhamento. O gestor aciona `Iniciar acompanhamento`, que faz
   importação idempotente + primeira transição, com autor e justificativa.
   **Não existe necessidade de cadastrar novamente o incidente ou recalcular prioridade**.
6. O histórico operacional fica no schema `operacional`. Reexecutar Airflow
   não altera etapas, comentários ou autorias; o score de entrada permanece
   uma fotografia, enquanto a visão pública reflete a pontuação corrente.

## Demonstração

Na consulta pública, o visitante pode ativar o recurso de simulação,
selecionar etapas para cartões e observar a mudança **somente na sessão
do próprio navegador**. A aplicação não envia requisições de escrita,
não altera `gold`, não grava `operacional` e não expõe um endpoint público
para atualizar status. É visualização demonstrativa, não andamento real.

A atualização persistente é exclusiva da gestão autenticada, com CSRF,
autorização de perfil, controle otimista de versão e histórico transacional.

## Indicadores

**Painel público:** total de ocorrências, distritos representados, score médio,
quantidade de pontuações na faixa elevada, categorias, distritos e
distribuição por faixa. Esses gráficos usam a fotografia atual e **não são
uma série temporal**.

**Gestão:** total de acompanhamentos, atendimentos em curso, conclusões
validadas e transições dos sete dias anteriores, agrupadas pela data
registrada em `operacional.historico_status`. A ausência de eventos
retorna zero, sem gerar dados fictícios.

## Segurança e implantação

- A consulta pública usa `app_reader` e somente `SELECT` na Gold.
- A projeção de status da gestão usa uma conexão operacional separada.
  Se ela estiver indisponível, a consulta pública segue disponível
  e exibe ausência de atualização operacional.
- Cadastro excepcional/manual legado permanece restrito à API interna,
  mas não é a entrada principal da aplicação.
- O catálogo não expõe nomes dos relatores, endereços individuais,
  autores da auditoria ou credenciais.
- Não há migrações adicionais; reutilizamos `migrations/001_operacional.sql`
  e `002_usuarios.sql`, que devem estar aplicadas no banco de gestão.
- Commit na `main` aciona **CI**, não faz deploy. O CD permanece manual
  via GitHub Actions/OIDC e exige configuração correta na Azure.

## Validação

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Verificar também por HTTP:

- `GET /` retorna painel público sem autenticação;
- `GET /ocorrencias?q=<ID>` retorna resultados correspondentes;
- `GET /api/ocorrencias` contém `total`, `itens`, `pagina`, `paginas`;
- `GET /ocorrencias/<ID>` mostra o fundamento técnico;
- a simulação não produz escrita;
- `POST /api/gestao/acompanhar` exige login, CSRF e gestor;
- o segundo encaminhamento do mesmo cluster preserva a versão e histórico;
- `/health` (processo) e `/ready` (PostgreSQL) continuam com contratos anteriores.

Projeto acadêmico demonstrativo: não apresentar como sistema municipal implantado.
