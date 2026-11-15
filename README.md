# Fila Justa — Ficha Técnica do MVP

**Nome do produto:** Fila Justa

**Público-alvo:** Gestores públicos, inicialmente no município de São Paulo, com modelo de dados preparado para expansão a outros municípios brasileiros.

**Problema:** A prefeitura recebe mais ocorrências urbanas do que consegue resolver, e os dados nem sempre ajudam a determinar quais devem ser atendidas primeiro.

**Proposta de valor:** Oferecer uma fila de priorização justa, explicável e sensível ao clima, considerando a sub-representação das áreas que registram menos reclamações.

## Arquitetura

- **Pipeline de dados:** Apache Airflow e PostgreSQL locais.
- **Camada analítica:** schema `gold`, incluindo `gold.mart_fila_priorizacao`.
- **Aplicação web:** em desenvolvimento para Azure App Service.
- **Banco em nuvem:** Azure Database for PostgreSQL.
- **CI/CD:** GitHub Actions.
- **Monitoramento:** Azure Application Insights.

## Fontes de dados

- SP156 — Prefeitura de São Paulo
- IBGE — Censo 2022
- Open-Meteo — dados meteorológicos
- Relatos simulados de aplicativo

## Inteligência Artificial

Modelos utilizados: a preencher conforme as demais disciplinas.

## Indicadores de impacto

A definir, incluindo análise da priorização com e sem correção de equidade.

## Objetivos de Desenvolvimento Sustentável

ODS 9, 10, 11 e 13.

## Links

- **Repositório:** https://github.com/jorgebooz/fila-justa-mvp
- **Aplicação pública:** em desenvolvimento

## Limitações atuais

O pipeline de dados funciona localmente. A arquitetura de nuvem utilizará um snapshot do schema `gold`, atualizado por cargas controladas.
As funcionalidades da aplicação web e os serviços Azure ainda serão implementados.