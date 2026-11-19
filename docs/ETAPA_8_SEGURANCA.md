# Etapa 8 — Segurança, auditoria e pendência de conectividade

**Projeto:** Fila Justa — MVP acadêmico na Azure  
**Estado da entrega acadêmica:** **CONCLUÍDA COM RESSALVA DOCUMENTADA** — auditoria executada e aplicação operacional; isolamento de rede do PostgreSQL permanece como melhoria técnica pendente.  
**Decisão acadêmica:** conforme confirmação informada pelo responsável pelo projeto, o professor aceitou a continuidade da entrega **desde que a limitação fique documentada**. A exceção de firewall está descrita aqui; a arquitetura não está atestada para produção com dados reais.

## Arquitetura envolvida

- App Service Linux no plano **F1**: `app-fila-justa-4b9b51`, região `northcentralus`.
- Azure Database for PostgreSQL Flexible Server: `psql-fila-justa-4b9b51`, região `northcentralus`, acesso público habilitado e transporte seguro obrigatório.
- Consulta pública ao schema `gold` com a identidade `app_reader`, apenas leitura.
- Gestão de demandas no schema `operacional` com `app_operador`, permissões restritas às tabelas necessárias e sem atualização na Gold.
- Teste do Application Insights em `/ready`, que verifica a consulta ao PostgreSQL. `/health` verifica somente o processo Flask.

## O que foi validado

| Controle | Evidência e resultado |
|---|---|
| HTTPS | `httpsOnly=true` no App Service |
| TLS | Mínimo TLS 1.2 no App Service; `require_secure_transport=on` no PostgreSQL |
| FTP/FTPS | `ftpsState=Disabled` |
| Depuração remota | Desabilitada |
| Credenciais | Configurações do App Service, não versionadas no Git |
| RBAC | Identidades administrativas revisadas: Owner e User Access Administrator herdados; confirmar periodicamente a necessidade dos acessos |
| Privilégios do banco | `app_reader` somente leitura; `app_operador` pode inserir/atualizar demandas, mas não inserir usuários nem atualizar Gold |
| CI/CD | Identidade federada OIDC do GitHub Actions com permissão de publicação limitada ao App Service; deploy manual testado |
| Integridade funcional | `/health` e `/ready` HTTP 200, fila Gold com 11.163 registros, login e fluxo operacional testados |

## Pendência — regra de firewall ampla para serviços Azure

**Regra:** `fj-f1-azure-acesso`, com o endereço especial `0.0.0.0` no firewall do Flexible Server. Esse valor não equivale a liberar toda a internet: habilita conexões originadas de serviços na Azure, **inclusive de outras assinaturas/locatários**. A autenticação PostgreSQL continua obrigatória.

**Testes realizados:**

1. Foram autorizados os quatro endereços públicos de saída informados pelo App Service: `52.240.159.79`, `52.240.153.20`, `52.240.157.160` e `52.240.158.91`.
2. Após remover a regra especial de acesso por serviços Azure, o aplicativo continuou respondendo `/health = 200`, mas `/ready = 503` e a página principal `/ = 503`; o PostgreSQL deixou de ser acessível pela aplicação.
3. A restauração controlada da regra `0.0.0.0` restabeleceu `/ready = 200` e `/ = 200`.
4. As migrações operacionais e a publicação por GitHub Actions/OIDC foram validadas posteriormente, com testes de login, demanda, histórico, indicadores e importação da Gold.

**Interpretação:** existe uma diferença não resolvida entre a origem efetiva da conexão do App Service e as regras restritas configuradas. Os testes mostram uma dependência da regra especial, mas **não comprovam a causa exata** do comportamento de roteamento. Não afirmar que a conexão é privada ou que a regra ampla é equivalente a uma lista de IPs específicos.

## Por que não foi resolvida nesta entrega

- A assinatura é **Azure for Students**, com cota **B1 igual a zero** para a região consultada.
- O **App Service F1** não dispõe de integração com rede virtual necessária à arquitetura recomendada de acesso privado ao banco.
- Não havia autorização/capacidade de provisionar um plano superior para integrar App Service, VNet, DNS privado e endpoint privado do PostgreSQL.
- Retirar a regra sem uma alternativa validada derrubou a leitura da fila e a disponibilidade da aplicação. Optou-se por preservar o MVP operacional para testes acadêmicos, **com risco identificado e documentado como ressalva da entrega acadêmica**, e não por afirmar que a pendência foi eliminada.

## Riscos e medidas compensatórias

**Risco residual:** outros serviços hospedados na Azure podem alcançar a superfície de rede do PostgreSQL e tentar autenticar-se. Uma falha de credenciais ou configuração de permissões pode elevar o impacto. TLS e papéis mínimos **reduzem o risco, mas não substituem isolamento de rede**.

**Medidas mantidas:** HTTPS/TLS, senhas fortes fora do Git, separação `app_reader`/`app_operador`, mínimo privilégio, histórico operacional, Application Insights, `/ready` e publicação manual controlada. Revisar periodicamente acessos e alertas; não expor credenciais em logs, prints ou documentação.

## Condição para encerrar a pendência de rede

1. Obter um plano e uma topologia que suportem integração de rede privada, sujeito à cota, orçamento e política da assinatura; ou demonstrar por testes uma alternativa com regras estritas realmente funcional no F1.
2. Configurar acesso privado ao PostgreSQL, DNS e regras apropriadas; validar a conexão `/ready` e o ciclo completo de gestão.
3. **Somente após testes bem-sucedidos**, remover a exceção `fj-f1-azure-acesso` e, quando aplicável, desabilitar o acesso público ao PostgreSQL.
4. Registrar nova evidência técnica e atualizar este documento.

**Status da Etapa 8:** **CONCLUÍDA COM RESSALVA DOCUMENTADA**, conforme aceite acadêmico informado pelo responsável pelo projeto. Pendência de isolamento de rede **aberta**. Adequação a produção com dados reais: **não atestada**.

## Pendência correlata de monitoramento (Etapa 10)

Teste de disponibilidade `fj-disponibilidade-banco` e alerta vinculados ao grupo `fj-alertas-disponibilidade` (1 e-mail configurado). O teste manual de envio de notificação retornou `409 Conflict — Free subscription not supported` para a operação `microsoft.insights/actiongroups/createNotifications/action`. **A configuração foi validada, mas a entrega do e-mail não foi comprovada.** Não tratar isso como falha do PostgreSQL nem como confirmação de que alertas reais não funcionam.
