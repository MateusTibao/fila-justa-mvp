# Fila Justa — Etapa 1 (implementação incremental)

## Auditoria em 17/11/2026

A branch `main` deste repositório continha um aplicativo Flask mínimo:
`GET /` mostra somente as 30 primeiras posições de `gold.mart_fila_priorizacao`,
`GET /health` verifica o PostgreSQL; não havia rotas de escrita, Kanban,
login interno, dashboards operacionais ou integração GenAI versionados na main.
O deploy existente pode estar usando outros arquivos: **não publicar esta branch
automaticamente antes de reconciliar o código de produção**.

## Primeiro incremento (este PR)

- Regras de seis estados e autorizações de transição.
- Cálculo de prazo separado do status (em dia / próximo / atrasado).
- Migração SQL isolada `operacional` para demandas e eventos de auditoria.
- Testes unitários para regras de status, autorização e fuso horário.
- Nenhuma alteração em `app.py`, `gold`, `app_reader`, CI/deploy ou Azure.

## Validação local

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

A migração foi criada **mas não aplicada** no banco de testes ou no Azure.
Ela deverá ser executada manualmente em ambiente de teste, usando papel de
migração e após verificação/backup. Não executar com `app_reader`.

## Integração posterior antes de concluir a Etapa 1

O pacote local da Etapa 1 já contém repositório SQLAlchemy, Blueprint Flask,
templates Kanban, JavaScript, CSS e testes de persistência (17 testes locais).
Esses componentes ainda precisam ser portados para esta branch e adaptados à
autenticação REAL do aplicativo. Por padrão, nenhuma API de escrita deve estar
publicamente disponível sem login, autorização e CSRF. Usar usuário de banco
separado, com escrita apenas no schema `operacional`.

## Critério de aceite

- Login/CSRF e papéis reais comprovados no repositório final.
- SQL em PostgreSQL de teste, criação, edição e transições com histórico persistente.
- Conflito entre versões respondendo HTTP 409.
- Reimportação de cluster mantém status; reprocessar Gold não altera demanda.
- Kanban acessível com mouse e teclado; não carregar os 11.163 clusters por padrão.
- Testes unitários, integração e regressão do app existente aprovados.
- Só depois decidir merge e deploy controlado no Azure.
