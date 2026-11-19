# Fila Justa — fluxo de consulta e gestão

## Duas áreas de navegação

- **Público**, acessível em `/`: busca por título ou ID, consulta paginada,
  detalhes, score de prioridade e situação atual sem login. Indicadores
  agregados ficam em uma seção expansível nessa mesma página.
- **Gestor**, acessível em `/gestao/kanban`: login institucional; Kanban
  na parte superior, entradas priorizadas da Gold na parte inferior; o gestor
  encaminha demandas recebidas e registra evolução do atendimento.

O cabeçalho é compartilhado entre as páginas públicas, login, detalhamento
e gestão, com os mesmos dois links. As rotas auxiliares de autenticação,
detalhes, APIs, saúde e arquivos estáticos continuam necessárias, mas não
são itens de navegação. As antigas páginas separadas de catálogo,
dashboard e listagem redirecionam para as áreas principais.

## Origem dos dados

O pipeline Airflow recebe dados do SP156, IBGE, clima e relatos simulados,
padroniza-os e publica uma fotografia analítica na
`gold.mart_fila_priorizacao`. O aplicativo Flask **não consulta diretamente
esses sites a cada solicitação** nem cria solicitações oficiais.
A home utiliza por orientação editorial o texto sobre SP156, clima, território
e equidade, sem mencionar relatos simulados no parágrafo de introdução.
**Os dados simulados não são removidos da fonte**.

A Gold fornece `cluster_id`, `rank`, tipo, distrito, score e explicação.
A consulta pública mostra o estágio vindo da camada operacional quando existe
vínculo; caso contrário mostra `Sem acompanhamento registrado`.

## Operação: atualização auditável

1. Registros não acompanhados aparecem abaixo do Kanban, pela ordem
   calculada pelo pipeline.
2. O gestor pode encaminhar um cartão para triagem. A operação materializa
   o acompanhamento uma vez só, preservando a Gold somente leitura.
3. O gestor abre um cartão pelo clique; arrastar também abre a confirmação
   em vez de salvar de forma silenciosa.
4. Escolhe a próxima etapa permitida **ou mantém a etapa atual**.
   **Em ambos os casos, a interface exige uma justificativa**.
5. No caso de manutenção da etapa, o evento recebe
   `tipo_evento=edicao`, `status_anterior=status_novo` e avança a versão,
   sem alterar a coluna do Kanban.
6. Todas as ações preservam autor, justificativa e data/hora no banco.
   Tokens CSRF e versão otimista são verificados; conflito retorna HTTP 409.

A UI não oferece mais cadastro manual, edição de título/distrito/tipo/prazo,
importação técnica avulsa ou painéis administrativos separados.
As rotas HTTP correspondentes foram removidas. O banco mantém os dados
e as regras existentes, sem migração nesta etapa.

## Datas

As datas são exibidas como `dd/mm/aaaa`, sem hora. O prazo é
**vencido a partir do dia seguinte** à data prevista, no fuso de São Paulo,
quando o atendimento ainda está aberto. A visualização mantém
`Prazo vencido` para registros nessa condição.
Os timestamps originais persistem para auditoria.

## Retenção da fila após conclusão

Uma demanda continua na coluna `Concluída` por **48 horas contadas do evento
de transição para resolvida**, não da última alteração administrativa.
O evento é identificado no histórico operacional, que não é apagado.
Anotações posteriores sem mudança de estado não prolongam a janela.

Após as 48 horas, o ID deixa de participar das consultas do **Kanban** e
da **fila pública de priorização**, incluindo busca, paginação, indicadores,
API e acesso público ao detalhe. A consulta autenticada direta ao histórico
continua possível para auditoria. Reabertura traz a demanda de volta;
uma nova conclusão reinicia o prazo.

O cálculo é feito ao consultar, sem job agendado; o Kanban se atualiza a cada
minuto quando está aberto e sem modal ativo. A Gold original continua
intacta, sem exclusão física nem alteração no pipeline. O serviço de leitura
retira os clusters expirados usando a conexão da base operacional, que deve
estar configurada em produção. Se configurada e fora do ar, falha sem
reexpor registros concluídos. Se a configuração operacional estiver ausente,
não há como conhecer os clusters finalizados e o filtro não funciona.

Nenhuma migração é necessária. Os testes verificam 47h59/48h, histórico
preservado, anotações posteriores, reabertura, Kanban, API e consulta pública.

## Segurança e limitações

O painel público não expõe históricos internos nem pessoas responsáveis.
A equipe precisa autenticar-se para registrar status; não é possível
editar a Gold por meio dessa interface. O funcionamento depende da
conexão da Gold e, para status operacional, da conexão separada.
O painel é um protótipo acadêmico demonstrativo.

## Verificações

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
node --check fj_operacional/static/kanban.js
```

Fluxos: `GET /`, `GET /?q=<id>`, `GET /ocorrencias/<id>`,
`GET /login`, `GET /gestao/kanban` e APIs de acompanhamento.
A versão do código é atualizada por commits diretos na `main`.
O Azure segue com deploy manual pelo CI/CD/OIDC, sem publicação
automática nesses commits.
