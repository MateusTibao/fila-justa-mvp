"""Contratos da consulta pública e gráficos — independentes do banco real."""
from fj_publico import titulo_ocorrencia, faixa_pontuacao, resumo_da_gold, normalizar_item, listar_gold


def test_titulo_e_prioridade_vem_da_fonte():
    assert titulo_ocorrencia('queda_arvore', 'Sé') == 'Queda arvore — Sé'
    assert faixa_pontuacao(84) == 'Elevada'
    assert faixa_pontuacao(57) == 'Intermediária'
    assert faixa_pontuacao(22) == 'Monitoramento'
    d = normalizar_item({'rank': 1, 'cluster_id': 'ID-1', 'tipo': 'buraco',
                         'area_nome':'Sé', 'score_0_100':84.556,
                         'n_relatos':3})
    assert d['titulo'] == 'Buraco — Sé'
    assert d['score_0_100'] == 84.56
    assert d['acompanhamento'] == 'nao_iniciado'
    assert d['n_relatos'] == 3


def test_graficos_refletem_quantidades_sem_inventar_tendencia():
    dados=[{'tipo':'buraco','area_nome':'Sé','score_0_100':85},
           {'tipo':'alagamento','area_nome':'Sé','score_0_100':65},
           {'tipo':'buraco','area_nome':'Tucuruvi','score_0_100':15}]
    resumo = resumo_da_gold(dados)
    assert resumo['total'] == 3
    assert resumo['areas'] == 2
    assert resumo['elevadas'] == 1
    assert resumo['tipos'][0]['nome'] == 'Buraco'
    assert resumo['tipos'][0]['total'] == 2
    assert resumo['faixas'][0]['total'] == 1
    assert resumo['media_score'] == 55.0


def test_catalogo_paginação_parametrizada_e_sem_escrita():
    queries=[]
    class Cursor:
        sql=''
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def execute(self,sql,params=()):
            self.sql=sql
            queries.append((sql,params))
        def fetchone(self): return {'total':81}
        def fetchall(self): return [
            {'rank':25,'cluster_id':'ref-25','tipo':'buraco','area_nome':'Sé',
             'score_0_100':76,'n_relatos':4,'explicacao':'Priorização explicável','run_id':'r1'}]
    class Conn:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def cursor(self): return Cursor()
    result = listar_gold(lambda: Conn(),busca="ID-25' OR 1=1 --",pagina=2,por_pagina=18)
    assert result['total'] == 81 and result['pagina'] == 2
    assert result['itens'][0]['titulo']=='Buraco — Sé'
    assert result['itens'][0]['score_0_100'] == 76
    assert len(queries)==2
    assert all(q[0].lstrip().upper().startswith('SELECT') for q in queries)
    assert "ID-25' OR 1=1 --" not in queries[0][0]
    assert queries[1][1][-2:] == [18,18]
    assert queries[0][1] == ["ID-25' OR 1=1 --"]
