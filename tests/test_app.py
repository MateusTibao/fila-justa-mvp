from unittest.mock import patch
import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()


def test_health_independent_of_database(client):
    with patch('app.check_database', side_effect=RuntimeError('Sem banco')) as db_check:
        response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {'status': 'healthy'}
    db_check.assert_not_called()


def test_ready_healthy(client):
    with patch('app.check_database', return_value=True):
        response = client.get('/ready')
    assert response.status_code == 200
    assert response.json == {'status': 'ready'}


def test_ready_degraded(client):
    with patch('app.check_database', return_value=False):
        response = client.get('/ready')
    assert response.status_code == 503
    assert response.json == {'status': 'degraded'}


def test_ready_handles_database_exception(client):
    with patch('app.check_database', side_effect=RuntimeError('Sem conexao')):
        response = client.get('/ready')
    assert response.status_code == 503
    assert response.json == {'status': 'degraded'}


def test_index_renders_priorities(client):
    dados = {'itens':[{'rank':1,'cluster_id':'C-1','titulo':'Buraco — Tucuruvi',
                     'area_nome':'Tucuruvi','score_0_100':51.55,
                     'score_pct':51.55,'faixa':'Intermediária','n_relatos':3,
                     'acompanhamento':'nao_iniciado'}]}
    resumo = {'total':1,'areas':1,'media_score':51.6,'elevadas':0,
              'tipos':[],'distritos':[],'faixas':[]}
    with patch('fj_publico.indicadores_gold', return_value=resumo), \
         patch('fj_publico.listar_gold', return_value=dados):
        response = client.get('/')
    assert response.status_code == 200
    assert 'Tucuruvi' in response.get_data(as_text=True)
    assert '51.55' in response.get_data(as_text=True)
    assert 'style="' not in response.get_data(as_text=True)
    assert '<progress' in response.get_data(as_text=True)


def test_index_handles_database_failure(client):
    with patch('fj_publico.indicadores_gold', side_effect=RuntimeError('Banco indisponível')):
        response = client.get('/')
    assert response.status_code == 503
    assert 'temporariamente indisponíveis' in response.get_data(as_text=True)


def test_catalogo_publico_sem_login(client):
    dados = {'itens':[{'rank':2,'cluster_id':'fj-02','titulo':'Alagamento — Sé',
                     'area_nome':'Sé','score_0_100':88,'score_pct':88,
                     'faixa':'Elevada','n_relatos':5,'acompanhamento':'nao_iniciado'}],
             'total':1,'pagina':1,'paginas':1,'busca':'fj-02'}
    with patch('fj_publico.listar_gold', return_value=dados) as consulta:
        response = client.get('/ocorrencias?q=fj-02')
    assert response.status_code == 200
    assert 'fj-02' in response.get_data(as_text=True)
    assert '88.00' in response.get_data(as_text=True)
    assert 'style="' not in response.get_data(as_text=True)
    assert consulta.call_args.kwargs['busca']=='fj-02'


def test_api_catalogo_publica(client):
    dados = {'itens':[],'total':0,'pagina':1,'paginas':1,'busca':''}
    with patch('fj_publico.listar_gold',return_value=dados):
        res = client.get('/api/ocorrencias')
    assert res.status_code==200 and res.json['itens']==[]


def test_detalhe_publico(client):
    registro = {'rank':1,'cluster_id':'c-1','titulo':'Buraco — Sé',
               'score_0_100':76,'n_relatos':2,'faixa':'Elevada',
               'area_nome':'Sé','acompanhamento':'nao_iniciado',
               'explicacao':'Pontuação calculada por equidade.'}
    with patch('fj_publico.obter_gold',return_value=registro):
        res=client.get('/ocorrencias/c-1')
    assert res.status_code==200
    assert 'Pontuação calculada por equidade' in res.get_data(as_text=True)


def test_login_indisponivel_sem_config(client):
    if not app.config.get('OP_ENGINE'):
        assert client.get('/login').status_code == 503
