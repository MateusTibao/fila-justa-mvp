"""Consulta pública paginada da fila analítica; nenhuma escrita na Gold."""
from collections import Counter
from datetime import timezone
from decimal import Decimal
from math import ceil


def titulo_ocorrencia(tipo, area):
    categoria = (str(tipo or "Ocorrência urbana").replace("_", " ").strip()).capitalize()
    local = str(area or "Localidade não informada").strip()
    return f"{categoria} — {local}"


def faixa_pontuacao(score):
    """Faixas ilustrativas do painel, não um SLA nem classificação oficial."""
    try:
        n = float(score)
    except (ValueError, TypeError):
        n = 0
    if n >= 75:
        return "Elevada"
    if n >= 50:
        return "Intermediária"
    return "Monitoramento"


def normalizar_item(row, acompanhamento=None):
    obj = dict(row)
    obj["cluster_id"] = str(obj.get("cluster_id") or "")
    obj["titulo"] = titulo_ocorrencia(obj.get("tipo"), obj.get("area_nome"))
    score = obj.get("score_0_100")
    obj["score_0_100"] = round(float(score), 2) if score is not None else None
    obj["score_pct"] = max(0, min(100, float(score))) if score is not None else 0
    obj["faixa"] = faixa_pontuacao(score)
    obj["n_relatos"] = int(obj.get("n_relatos") or 0)
    obj["acompanhamento"] = acompanhamento or "nao_iniciado"
    obj["prazo_data"] = None
    obj["prazo_vencido"] = False
    # Não compartilhar autores, usuários, observações internas ou dados pessoais.
    obj["explicacao"] = str(obj.get("explicacao") or "")[:500]
    return obj


def resumo_da_gold(rows):
    """Agregados reais da fotografia consultada; não inventa série temporal."""
    registros = [dict(r) for r in rows]
    tipos = Counter(str(r.get("tipo") or "Não classificado").replace("_", " ").capitalize()
                    for r in registros)
    areas = Counter(str(r.get("area_nome") or "Não informado") for r in registros)
    scores = [float(r["score_0_100"]) for r in registros if r.get("score_0_100") is not None]
    faixas = Counter(faixa_pontuacao(s) for s in scores)
    total = len(registros)
    return {
        "total": total, "areas": len(areas),
        "media_score": round(sum(scores)/len(scores),1) if scores else 0,
        "elevadas": faixas.get("Elevada",0),
        "tipos": [{"nome":k,"total":v,"percentual":round(100*v/total,1) if total else 0}
                  for k,v in tipos.most_common(6)],
        "distritos": [{"nome":k,"total":v,"percentual":round(100*v/total,1) if total else 0}
                      for k,v in areas.most_common(6)],
        "faixas": [{"nome":nome,"total":faixas.get(nome,0),
                   "percentual":round(100*faixas.get(nome,0)/total,1) if total else 0}
                   for nome in ("Elevada","Intermediária","Monitoramento")],
    }


def _obter_acompanhamento(engine, ids):
    if engine is None or not ids:
        return {}
    from sqlalchemy import select
    from fj_operacional.models import demandas
    with engine.connect() as conn:
        rows = conn.execute(select(demandas.c.cluster_id, demandas.c.status,
                                   demandas.c.prazo_em)
                            .where(demandas.c.cluster_id.in_(ids))).all()
    return {str(cluster): {"status": status, "prazo": prazo}
            for cluster, status, prazo in rows}


def aplicar_acompanhamento(itens, engine=None, log=None):
    try:
        estados = _obter_acompanhamento(engine, [i["cluster_id"] for i in itens])
    except Exception:
        # Consulta pública deve continuar disponível mesmo com operação indisponível.
        if log:
            log.warning("Acompanhamento operacional indisponível na consulta pública")
        estados = {}
    from fj_operacional.domain import data_prazo, prazo_atrasado
    for item in itens:
        registro = estados.get(item["cluster_id"])
        if not registro:
            item["acompanhamento"] = "nao_iniciado"
            continue
        item["acompanhamento"] = registro["status"]
        prazo = registro["prazo"]
        if prazo is not None:
            if prazo.tzinfo is None:
                prazo = prazo.replace(tzinfo=timezone.utc)
            item["prazo_data"] = data_prazo(prazo).strftime("%d/%m/%Y")
            item["prazo_vencido"] = prazo_atrasado(registro["status"], prazo)
    return itens


def listar_gold(get_connection, *, busca="", pagina=1, por_pagina=18, engine=None, log=None):
    busca = str(busca or "").strip()[:120]
    try:
        pagina = max(1, min(int(pagina), 10000))
    except (TypeError, ValueError):
        pagina = 1
    por_pagina = max(1, min(int(por_pagina), 30))
    where = ("WHERE POSITION(LOWER(%s) IN LOWER("
             "COALESCE(cluster_id::text, '') || ' ' || COALESCE(tipo::text, '') || ' ' ||"
             "COALESCE(area_nome::text, '') || ' ' || "
             "COALESCE(tipo::text, '') || ' — ' || COALESCE(area_nome::text, '')"
             ")) > 0") if busca else ""
    params = [busca] if busca else []
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total FROM gold.mart_fila_priorizacao " + where, params)
            total = int(cursor.fetchone()["total"])
            cursor.execute("""
                SELECT rank, cluster_id, tipo, area_nome,
                       ROUND(score_0_100::numeric, 2) AS score_0_100,
                       n_relatos, explicacao, run_id
                  FROM gold.mart_fila_priorizacao
            """ + where + " ORDER BY rank ASC NULLS LAST, cluster_id LIMIT %s OFFSET %s",
                           params + [por_pagina, (pagina-1)*por_pagina])
            itens = [normalizar_item(r) for r in cursor.fetchall()]
    return {"itens": aplicar_acompanhamento(itens,engine,log),
            "total": total, "pagina": pagina, "por_pagina": por_pagina,
            "paginas": max(1,ceil(total/por_pagina)), "busca": busca}


def obter_gold(get_connection, cluster_id, *, engine=None, log=None):
    cluster_id = str(cluster_id or "")[:300]
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT rank, cluster_id, tipo, area_nome,
                       ROUND(score_0_100::numeric, 2) AS score_0_100,
                       n_relatos, explicacao, run_id
                  FROM gold.mart_fila_priorizacao
                 WHERE cluster_id::text = %s LIMIT 1
            """,(cluster_id,))
            row = cursor.fetchone()
    if row is None:
        return None
    return aplicar_acompanhamento([normalizar_item(row)],engine,log)[0]


def indicadores_gold(get_connection):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT tipo, area_nome, score_0_100
                  FROM gold.mart_fila_priorizacao
            """)
            rows = cursor.fetchall()
    return resumo_da_gold(rows)
