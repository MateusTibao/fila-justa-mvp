"""Retenção de demandas concluídas: 48 horas na fila, histórico preservado.

Consulta a data da última TRANSIÇÃO para concluída; atualizações com a
mesma etapa não renovam a permanência. Reabertura retira o filtro.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select

from .models import demandas, historico

PERMANENCIA_CONCLUIDA = timedelta(days=2)


def finalizacao_expirada(concluida_em, *, agora=None):
    """Regra determinística, inclusive no instante exato das 48 horas."""
    if concluida_em is None:
        return False
    if concluida_em.tzinfo is None:
        concluida_em = concluida_em.replace(tzinfo=timezone.utc)
    agora = agora or datetime.now(timezone.utc)
    if agora.tzinfo is None:
        agora = agora.replace(tzinfo=timezone.utc)
    return concluida_em + PERMANENCIA_CONCLUIDA <= agora


def consultar_expiradas(engine, *, agora=None):
    """Retorna IDs operacionais e clusters expirados; somente leitura."""
    agora = agora or datetime.now(timezone.utc)
    limite = agora - PERMANENCIA_CONCLUIDA
    ultima = (
        select(
            historico.c.demanda_id.label("demanda_id"),
            func.max(historico.c.ocorrido_em).label("concluida_em"),
        )
        .where(
            historico.c.tipo_evento == "transicao",
            historico.c.status_novo == "resolvida",
        )
        .group_by(historico.c.demanda_id)
        .subquery()
    )
    # O status atual protege reaberturas. MAX ignora anotação sem mudança.
    consulta = (
        select(demandas.c.id, demandas.c.cluster_id)
        .join(ultima, ultima.c.demanda_id == demandas.c.id)
        .where(demandas.c.status == "resolvida", ultima.c.concluida_em <= limite)
    )
    with engine.connect() as conn:
        registros = conn.execute(consulta).all()
    return {
        "ids": {str(identificador) for identificador, _ in registros},
        "clusters": {str(cluster) for _, cluster in registros if cluster},
    }
