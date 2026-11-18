# Etapa 13 — Relatório final e roteiro da entrega Cloud

**Data de referência:** 18/11/2026  
**Aplicação:** https://app-fila-justa-4b9b51.azurewebsites.net  
**Repositório:** https://github.com/MateusTibao/fila-justa-mvp

O relatório final foi produzido em **PDF A4 com oito páginas e capturas reais**, disponibilizado como anexo na conversa de entrega. Este documento deixa o roteiro e as condições de aceite versionados no repositório. O arquivo binário PDF não foi publicado automaticamente no GitHub.

## Passo a passo das 13 etapas

| Etapa | Trabalho realizado | Situação |
|---|---|---|
| 1 | Planejamento da priorização urbana e arquitetura analítica/operacional | Concluída |
| 2 | GitHub com código, testes e documentação: `MateusTibao/fila-justa-mvp` | Concluída |
| 3 | Resource Group `rg-fila-justa` na assinatura Azure for Students | Concluída |
| 4 | PostgreSQL Flexible Server com snapshot Gold; migrações do schema `operacional` | Concluída |
| 5 | MVP Flask: fila pública, login, demandas, Kanban, histórico e indicadores | Testes funcionais principais aprovados |
| 6 | App Service F1 na Azure, HTTPS, Python e variáveis de ambiente | Concluída |
| 7 | Application Insights integrado à aplicação e com telemetria HTTP | Concluída |
| 8 | Auditoria e regras de firewall; isolamento de rede pendente de solução | **EM CONFIRMAÇÃO do professor** |
| 9 | CI GitHub Actions, OIDC e publicação manual no App Service | Concluída; [deploy aprovado](https://github.com/MateusTibao/fila-justa-mvp/actions/runs/44240763220) |
| 10 | Teste de disponibilidade `/ready`, regra de alerta e grupo com e-mail | Configurada; envio real do e-mail não confirmado |
| 11 | Custos iniciais observados no Azure; revisão total posterior aos testes | Revisão final pendente |
| 12 | Arquitetura, dados, segurança, operação e evidências documentadas | Concluída |
| 13 | Relatório prático da entrega em PDF A4 e roteiro de demonstração | PDF produzido |

## Evidências confirmadas

- `/health` e `/ready` responderam HTTP 200 nas verificações do deploy.
- O teste de disponibilidade no Application Insights mostrou cinco verificações bem-sucedidas, sem falhas, no recorte apresentado.
- A Gold continha 11.163 registros na validação da migração.
- Conta gestora acessou o Kanban; demanda de teste percorreu o fluxo até `resolvida`, com histórico.
- Indicadores de teste: 1 demanda total, 1 resolvida, 0 ativas, 0 atrasadas.
- Uma ocorrência Gold de `buraco` no Tucuruvi foi importada por cluster ID; reimportação preservou status e versão na interface.

## Roteiro de apresentação

1. Apresentar o problema de priorização urbana e as fontes de dados.
2. Mostrar as camadas Bronze, Silver e Gold, deixando claro que o pipeline foi validado fora da Azure e que a aplicação consulta um snapshot Gold na nuvem.
3. Abrir a fila pública e explicar as 30 prioridades exibidas.
4. Entrar com a conta gestora de demonstração e abrir Kanban, demandas, histórico e indicadores.
5. Mostrar a importação de um cluster Gold e a reimportação sem reiniciar o atendimento.
6. Abrir a execução de deploy bem-sucedida do GitHub Actions.
7. Apresentar o monitoramento /ready e a regra de alerta vinculada ao grupo de ações.
8. Explicar que a Etapa 8 está **em confirmação**, pois a limitação de firewall do plano F1 foi submetida ao professor.
9. Explicar que o e-mail de alerta não foi comprovado devido ao erro `409 Conflict — Free subscription not supported` no teste manual da assinatura.
10. Revalidar os custos reais da assinatura antes do encerramento definitivo.

## Limitações que não devem ser apresentadas como concluídas

- **Etapa 8:** sem confirmação do professor e sem isolamento privado do PostgreSQL.
- **Etapa 10:** configuração comprovada, notificação recebida por e-mail não comprovada.
- **Etapa 11:** valor inicial de US$ 0,04 no grupo de recursos, mas custo total de assinatura e orçamento mensal ainda sujeitos à revisão.
- O projeto é protótipo acadêmico; não é serviço oficial da Prefeitura e não há indicação de Airflow operando continuamente na Azure.

## Documentos relacionados

- [Arquitetura Cloud — Etapa 12](ETAPA_12_ARQUITETURA_CLOUD.md)
- [Segurança — Etapa 8](ETAPA_8_SEGURANCA.md)
- [CI/CD e OIDC](CI_CD.md)
- [README](../README.md)
