"""Testes HTTP: público e gestor, com estado operacional isolado."""
from datetime import datetime, timezone
import pytest
from flask import Flask
from sqlalchemy import create_engine, update
from sqlalchemy.pool import StaticPool
from fj_operacional import criar_blueprint
from fj_operacional.models import metadata, demandas

@pytest.fixture
def contexto():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    with engine.begin() as conn:
        conn.exec_driver_sql("ATTACH DATABASE ':memory:' AS operacional")
        conn.exec_driver_sql("ATTACH DATABASE ':memory:' AS gold")
        metadata.create_all(conn)
        conn.exec_driver_sql('CREATE TABLE gold.mart_fila_priorizacao (rank INTEGER, cluster_id TEXT, tipo TEXT, area_nome TEXT, score_0_100 REAL, run_id TEXT)')
        conn.exec_driver_sql("INSERT INTO gold.mart_fila_priorizacao VALUES (1,'teste1','buraco','Sé',90,'runA')")
    app=Flask(__name__)
    app.config.update(TESTING=True,SECRET_KEY='test-only-secret')
    estado={'usuario':None,'engine':engine}
    app.add_url_rule('/','index',lambda:'consulta pública')
    app.add_url_rule('/login','login',lambda:'entrar')
    app.add_url_rule('/logout','logout',lambda:'sair',methods=['POST'])
    app.register_blueprint(criar_blueprint(engine=engine,
        usuario_atual=lambda:estado['usuario'],
        validar_csrf=lambda req:req.headers.get('X-CSRFToken')=='token-valido',
        token_csrf=lambda:'token-valido'))
    yield app.test_client(),estado
    engine.dispose()

HEADERS={'X-CSRFToken':'token-valido'}

def test_rotas_gestor_exigem_login_e_nao_expoem_cadastro(contexto):
    client,estado=contexto
    assert client.get('/api/gestao/demandas').status_code==401
    assert client.get('/api/gestao/entrada').status_code==401
    assert client.get('/gestao/kanban').status_code==302
    estado['usuario']={'id':'gestor','perfil':'gestor'}
    assert client.post('/api/gestao/demandas',json={'titulo':'Novo'}).status_code==405
    assert client.patch('/api/gestao/demandas/qualquer',json={'titulo':'A'}).status_code==405
    assert client.post('/api/gestao/importar-gold',json={'cluster_id':'teste1'}).status_code==404
    assert client.get('/gestao/demandas').status_code==302
    assert client.get('/gestao/dashboard').status_code==302

def test_fluxo_de_acompanhamento_justificativa_mesma_etapa_e_versao(contexto):
    client,estado=contexto
    estado['usuario']={'id':'gestor','perfil':'gestor'}
    assert client.post('/api/gestao/acompanhar',json={'cluster_id':'teste1'}).status_code==403
    d=client.post('/api/gestao/acompanhar',json={'cluster_id':'teste1'},headers=HEADERS)
    assert d.status_code==200 and d.json['status']=='pendente'
    criado=d.json
    assert client.get('/api/gestao/entrada').json['itens']==[]
    assert client.get('/api/gestao/demandas').json['total']==1
    sem_just=client.post(f'/api/gestao/demandas/{criado["id"]}/status',
        json={'status':'pendente','versao':criado['versao'],'justificativa':'  '},headers=HEADERS)
    assert sem_just.status_code==422
    registro=client.post(f'/api/gestao/demandas/{criado["id"]}/status',
        json={'status':'pendente','versao':criado['versao'],
              'justificativa':'Aguardando equipe de manutenção'},headers=HEADERS)
    assert registro.status_code==200
    assert registro.json['status']=='pendente' and registro.json['versao']==criado['versao']+1
    conflito=client.post(f'/api/gestao/demandas/{criado["id"]}/status',
        json={'status':'pendente','versao':criado['versao'],'justificativa':'Duplicada'},headers=HEADERS)
    assert conflito.status_code==409
    hist=client.get(f'/api/gestao/demandas/{criado["id"]}/historico')
    assert hist.status_code==200 and len(hist.json)==3
    assert hist.json[-1]['tipo_evento']=='edicao'
    assert hist.json[-1]['status_anterior']==hist.json[-1]['status_novo']=='pendente'
    assert hist.json[-1]['justificativa']=='Aguardando equipe de manutenção'

def test_kanban_primeiro_demandas_depois_e_nav_unica(contexto):
    client,estado=contexto
    estado['usuario']={'id':'gestor','perfil':'gestor'}
    res=client.get('/gestao/kanban')
    assert res.status_code==200
    html=res.get_data(as_text=True)
    assert html.index('id="kanban"') < html.index('id="entrada-fila"')
    assert html.count('>Público</a>')==1
    assert html.count('>Gestor</a>')==1
    assert 'Cadastre uma demanda' not in html
    assert 'btn-nova' not in html
    assert 'btn-salvar' not in html
    assert 'id="justificativa"' in html
    assert 'Registrar atualização' in html
    assert 'style="' not in html

def test_entrada_gold_idempotente(contexto):
    client,estado=contexto
    estado['usuario']={'id':'gestor','perfil':'gestor'}
    assert client.get('/api/gestao/entrada').json['itens'][0]['cluster_id']=='teste1'
    for i in range(2):
        res=client.post('/api/gestao/acompanhar',json={'cluster_id':'teste1'},headers=HEADERS)
        assert res.status_code==200
        assert res.json['status']=='pendente'
    assert client.get('/api/gestao/demandas').json['total']==1

def test_prazo_vencido_continua_visivel_sem_edicao(contexto):
    client,estado=contexto
    estado['usuario']={'id':'gestor','perfil':'gestor'}
    d=client.post('/api/gestao/acompanhar',json={'cluster_id':'teste1'},headers=HEADERS).json
    with estado['engine'].begin() as conn:
        conn.execute(update(demandas).where(demandas.c.id==d['id']).values(
            prazo_em=datetime(2020,11,17,23,59,tzinfo=timezone.utc)))
    dados=client.get('/api/gestao/kanban').json
    assert dados['pendente']['itens'][0]['prazo_vencido'] is True
    assert dados['pendente']['itens'][0]['prazo_data']=='17/11/2020'
    html=client.get('/gestao/kanban').get_data(as_text=True)
    assert 'datetime-local' not in html
    assert 'type="text" inputmode="numeric"' not in html

def test_operador_nao_registra_edicao_em_concluida(contexto):
    client,estado=contexto
    estado['usuario']={'id':'gestor','perfil':'gestor'}
    d=client.post('/api/gestao/acompanhar',json={'cluster_id':'teste1'},headers=HEADERS).json
    for prox,perfil in [('em_andamento','operador'),('aguardando_validacao','operador'),
                        ('resolvida','gestor')]:
        estado['usuario']={'id':perfil,'perfil':perfil}
        d=client.post(f'/api/gestao/demandas/{d["id"]}/status',
          json={'versao':d['versao'],'status':prox,'justificativa':'Etapa conferida'},headers=HEADERS).json
    estado['usuario']={'id':'operador','perfil':'operador'}
    r=client.post(f'/api/gestao/demandas/{d["id"]}/status',
      json={'versao':d['versao'],'status':'resolvida','justificativa':'Tentativa'},headers=HEADERS)
    assert r.status_code==403
