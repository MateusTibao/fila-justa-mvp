-- Execute somente em ambiente de teste com identidade de migração.
-- Não altera gold, Airflow ou o usuário app_reader.
BEGIN;
CREATE SCHEMA IF NOT EXISTS operacional;
CREATE TABLE IF NOT EXISTS operacional.demandas (
  id TEXT PRIMARY KEY,
  origem TEXT NOT NULL CHECK (origem IN ('manual', 'gold')),
  cluster_id TEXT UNIQUE,
  run_id_origem TEXT,
  titulo TEXT NOT NULL CHECK (length(btrim(titulo)) BETWEEN 3 AND 160),
  descricao TEXT NOT NULL DEFAULT '',
  tipo TEXT,
  area_nome TEXT,
  score_origem DOUBLE PRECISION,
  status TEXT NOT NULL CHECK (status IN (
    'nova','pendente','em_andamento','aguardando_validacao','resolvida','cancelada')),
  prazo_em TIMESTAMPTZ,
  criado_por TEXT NOT NULL,
  criado_em TIMESTAMPTZ NOT NULL,
  atualizado_em TIMESTAMPTZ NOT NULL,
  versao INTEGER NOT NULL CHECK (versao >= 1),
  CONSTRAINT origem_cluster_consistente CHECK (
    (origem = 'gold' AND cluster_id IS NOT NULL) OR origem = 'manual')
);
CREATE TABLE IF NOT EXISTS operacional.historico_status (
  id TEXT PRIMARY KEY,
  demanda_id TEXT NOT NULL REFERENCES operacional.demandas(id) ON DELETE RESTRICT,
  tipo_evento TEXT NOT NULL CHECK (tipo_evento IN ('criacao','transicao','edicao')),
  status_anterior TEXT,
  status_novo TEXT NOT NULL,
  justificativa TEXT NOT NULL DEFAULT '',
  autor_id TEXT NOT NULL,
  ocorrido_em TIMESTAMPTZ NOT NULL,
  versao_nova INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_demandas_status
  ON operacional.demandas(status, atualizado_em DESC);
CREATE INDEX IF NOT EXISTS idx_historico_demanda
  ON operacional.historico_status(demanda_id, ocorrido_em);
COMMIT;
-- Conceda somente SELECT/INSERT/UPDATE em operacional.demandas,
-- SELECT/INSERT em operacional.historico_status ao papel operacional dedicado.
-- NUNCA conceda UPDATE/DELETE em gold ou no histórico de auditoria.
