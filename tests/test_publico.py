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

def test_prazo_vencido_na_consulta_publica():
    from datetime import datetime, timezone
    from unittest.mock import patch
    from fj_publico import aplicar_acompanhamento
    raw=[{'cluster_id':'c-1','acompanhamento':'nao_iniciado',
          'prazo_data':None,'prazo_vencido':False}]
    configurado={'c-1':{'status':'em_andamento',
                       'prazo':datetime(2020,11,18,2,59,59,tzinfo=timezone.utc)}}
    with patch('fj_publico._obter_acompanhamento',return_value=configurado):
        itens=aplicar_acompanhamento(raw,engine=object())
    assert itens[0]['prazo_data'] == '17/11/2020'
    assert itens[0]['prazo_vencido'] is True
    assert itens[0]['acompanhamento'] == 'em_andamento'

def test_filtro_publico_ignora_clusters_concluidos_apos_48_horas():
    from unittest.mock import patch
    from fj_publico import listar_gold, indicadores_gold, obter_gold
    executadas=[]
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,sql,params=()):
            executadas.append((sql,params))
        def fetchone(self):return {'total':1}
        def fetchall(self):
            return [{'rank':1,'cluster_id':'c-aberto','tipo':'buraco','area_nome':'Sé',
              'score_0_100':70,'n_relatos':1,'explicacao':'','run_id':'r'}]
    class Conn:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def cursor(self):return Cursor()
    with patch('fj_publico._clusters_ocultos',return_value={'c-concluido'}), \
         patch('fj_publico._obter_acompanhamento',return_value={}):
        dados=listar_gold(lambda:Conn(),busca='Sé',engine=object())
        assert dados['itens'][0]['cluster_id']=='c-aberto'
        assert dados['total']==1
        assert len(executadas)==2
        assert 'cluster_id::text <> ALL(%s)' in executadas[0][0]
        assert executadas[0][1] == [['c-concluido'],'Sé']
        assert executadas[1][1][-2:] == [18,0]
        assert obter_gold(lambda:Conn(),'c-concluido',engine=object()) is None
        assert len(executadas)==2
        indicadores_gold(lambda:Conn(),engine=object())
        assert 'cluster_id::text <> ALL(%s)' in executadas[-1][0]
        assert executadas[-1][1] == [['c-concluido']]


def test_filtro_fechado_quando_operacional_indisponivel():
    import pytest
    from unittest.mock import patch
    from fj_publico import listar_gold
    with patch('fj_operacional.retencao.consultar_expiradas',side_effect=OSError('falha de banco')):
        with pytest.raises(RuntimeError,match='operacional'):
            listar_gold(lambda:None, engine=object())
