'use strict';
// O gestor apenas registra movimentações e justificativas. A Gold define prioridades.
const CFG = {csrf:document.querySelector('meta[name="fj-csrf"]').content,
             perfil:document.body.dataset.perfil};
const URLS = {kanban:'/api/gestao/kanban',entrada:'/api/gestao/entrada',
              acompanhar:'/api/gestao/acompanhar',demandas:'/api/gestao/demandas'};
const ROTULOS = {nova:'Recebida',pendente:'Em triagem',em_andamento:'Em atendimento',
  aguardando_validacao:'Em conferência',resolvida:'Concluída',cancelada:'Arquivada'};
const PROXIMAS = {nova:['pendente','cancelada'],pendente:['em_andamento','cancelada'],
  em_andamento:['aguardando_validacao','cancelada'],
  aguardando_validacao:['em_andamento','resolvida','cancelada'],
  resolvida:['em_andamento'],cancelada:[]};
const gestor = ['gestor','administrador'].includes(CFG.perfil);
const el = id => document.getElementById(id);
const aviso = msg => { el('aviso').textContent = msg || ''; };
let atual = null;

async function api(url,method='GET',payload) {
  const headers={'Accept':'application/json'};
  if (payload!==undefined) {
    headers['Content-Type']='application/json';
    headers['X-CSRFToken']=CFG.csrf;
  }
  const resposta=await fetch(url,{method,headers,credentials:'same-origin',
    body:payload===undefined?undefined:JSON.stringify(payload)});
  let dados={};
  try {dados=await resposta.json();} catch {}
  if (!resposta.ok) throw new Error(dados.erro||'Falha ao consultar ou atualizar.');
  return dados;
}
function texto(tag,valor,classe) {
  const n=document.createElement(tag);
  n.textContent=valor == null ? '' : String(valor);
  if (classe)n.className=classe;
  return n;
}
function podeMudar(origem,destino) {
  if (!PROXIMAS[origem]?.includes(destino))return false;
  if (gestor)return true;
  return !['resolvida','cancelada','pendente'].includes(destino) && origem!=='resolvida';
}
function opcoes(origem) {
  const validas=[];
  if (gestor || !['resolvida','cancelada'].includes(origem))validas.push(origem);
  validas.push(...(PROXIMAS[origem]||[]).filter(s=>podeMudar(origem,s)));
  return validas;
}
function formatarData(iso) {
  if (!iso)return '';
  return new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',
    year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(iso));
}
function cartao(d) {
  const n=texto('article','', 'card');
  n.tabIndex=0;n.draggable=true;n.setAttribute('role','button');
  n.setAttribute('aria-label','Atualizar demanda: '+d.titulo);
  n.append(texto('h3',d.titulo),texto('p',d.area_nome||d.tipo||'Distrito não informado'));
  n.append(texto('span',d.score_origem==null?'Pontuação não disponível':
    'Prioridade: '+Number(d.score_origem).toFixed(2)+' / 100','badge'));
  if(d.prazo_data) {
    n.append(texto('span',d.prazo_vencido?'Prazo vencido':'Conclusão prevista: '+d.prazo_data,
      d.prazo_vencido?'badge prazo-vencido':'card-due'));
    if(d.prazo_vencido)n.append(texto('small','Previsão: '+d.prazo_data,'card-due'));
  }
  n.append(texto('small','ID: '+(d.cluster_id||d.id),'card-code'));
  n.addEventListener('click',()=>abrir(d.id));
  n.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();abrir(d.id);}});
  n.addEventListener('dragstart',e=>{e.dataTransfer.setData('text/plain',d.id);
                                      e.dataTransfer.effectAllowed='move';});
  return n;
}
async function carregar() {
  aviso('');
  try {
    const dados=await api(URLS.kanban);
    document.querySelectorAll('.column').forEach(col=>{
      const s=col.dataset.status;
      col.querySelector('.count').textContent=dados[s]?.total??0;
      col.querySelector('.cards').replaceChildren(...(dados[s]?.itens||[]).map(cartao));
    });
    await carregarEntrada();
  } catch(err) {aviso(err.message);}
}
async function carregarEntrada() {
  const alvo=el('entrada-fila');alvo.replaceChildren();
  try {
    const dados=await api(URLS.entrada);
    if(!dados.itens?.length){
      alvo.append(texto('p','Não há novos cartões entre as prioridades consultadas.'));
      return;
    }
    for(const d of dados.itens) {
      const box=texto('article','','inbox-card');
      box.append(texto('small','Posição #'+d.rank+' · ID: '+d.cluster_id),
                 texto('strong',d.titulo),
                 texto('span','Pontuação: '+Number(d.score_origem).toFixed(2)+' / 100','inbox-score'));
      const b=texto('button','Encaminhar para triagem');
      b.type='button';b.className='secondary';b.disabled=!gestor;
      b.addEventListener('click',async()=>{
        b.disabled=true;
        try {
          const registro=await api(URLS.acompanhar,'POST',{cluster_id:d.cluster_id});
          await carregar();
          await abrir(registro.id);
        } catch(err) {aviso(err.message);b.disabled=false;}
      });
      box.append(b);alvo.append(box);
    }
  } catch(err){alvo.append(texto('p','Entrada analítica temporariamente indisponível.'));}
}
async function abrir(id,destino) {
  try {
    atual=await api(URLS.demandas+'/'+encodeURIComponent(id));
    el('modal-erro').textContent='';
    el('modal-titulo').textContent=atual.titulo;
    el('dados-origem').textContent='ID: '+(atual.cluster_id||atual.id)+' · Pontuação: '+
      (atual.score_origem==null?'não informada':Number(atual.score_origem).toFixed(2)+' / 100');
    el('prazo-situacao').textContent=atual.prazo_vencido?'Prazo vencido · '+atual.prazo_data:
      (atual.prazo_data?'Conclusão prevista: '+atual.prazo_data:'');
    el('justificativa').value='';
    const select=el('novo-status');select.replaceChildren();
    for(const s of opcoes(atual.status)) {
      const option=document.createElement('option');
      option.value=s;option.textContent=ROTULOS[s]+(s===atual.status?' (manter etapa)':'');
      select.append(option);
    }
    select.value=destino&&opcoes(atual.status).includes(destino)?destino:atual.status;
    el('btn-transicao').disabled=!select.options.length;
    const h=await api(URLS.demandas+'/'+encodeURIComponent(id)+'/historico');
    const historico=el('historico');historico.replaceChildren(texto('h3','Histórico de atualizações'));
    for(const e of h) {
      const descricao=(e.status_anterior===e.status_novo?'Atualização na etapa: '+ROTULOS[e.status_novo]:
        (ROTULOS[e.status_anterior]||'Recebida')+' → '+ROTULOS[e.status_novo]);
      historico.append(texto('p',(e.ocorrido_data||formatarData(e.ocorrido_em))+
        ' · '+descricao+(e.justificativa?' · '+e.justificativa:'')));
    }
    el('detalhe').showModal();
  } catch(err){aviso(err.message);}
}
document.querySelectorAll('.column').forEach(col=>{
  col.addEventListener('dragover',e=>{e.preventDefault();col.classList.add('drag-over');});
  col.addEventListener('dragleave',()=>col.classList.remove('drag-over'));
  col.addEventListener('drop',async e=>{
    e.preventDefault();col.classList.remove('drag-over');
    const id=e.dataTransfer.getData('text/plain');if(!id)return;
    try {
      const d=await api(URLS.demandas+'/'+encodeURIComponent(id));
      if(d.status!==col.dataset.status&&!podeMudar(d.status,col.dataset.status)){
        aviso('A mudança de etapa selecionada não é permitida.');return;
      }
      await abrir(id,col.dataset.status);
      el('justificativa').focus();
    } catch(err){aviso(err.message);}
  });
});
el('fechar-modal').addEventListener('click',()=>el('detalhe').close());
el('btn-transicao').addEventListener('click',async()=>{
  if(!atual)return;
  const justificativa=el('justificativa').value.trim();
  if(!justificativa){el('modal-erro').textContent='Informe a justificativa para registrar a atualização.';return;}
  const botao=el('btn-transicao');botao.disabled=true;
  try {
    await api(URLS.demandas+'/'+encodeURIComponent(atual.id)+'/status','POST',
      {status:el('novo-status').value,versao:atual.versao,justificativa});
    el('detalhe').close();await carregar();
  } catch(err){el('modal-erro').textContent=err.message;}
  finally{botao.disabled=false;}
});
carregar();
const abrirId=new URLSearchParams(location.search).get('abrir');
if(abrirId&&/^[a-z0-9-]{1,300}$/i.test(abrirId))abrir(abrirId);
