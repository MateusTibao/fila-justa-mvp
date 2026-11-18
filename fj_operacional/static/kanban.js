'use strict';
const CFG = {csrf: document.querySelector('meta[name=fj-csrf]').content, perfil: document.body.dataset.perfil};
const ROTAS = {
  kanban: '/api/gestao/kanban',
  demandas: '/api/gestao/demandas',
  importar: '/api/gestao/importar-gold',
  entrada: '/api/gestao/entrada',
  acompanhar: '/api/gestao/acompanhar'
};
const PROXIMAS = {
  nova: ['pendente','cancelada'],
  pendente: ['em_andamento','cancelada'],
  em_andamento: ['aguardando_validacao','cancelada'],
  aguardando_validacao: ['em_andamento','resolvida','cancelada'],
  resolvida: ['em_andamento'], cancelada: []
};
const LABELS = {
  nova: 'Recebida', pendente: 'Em triagem', em_andamento: 'Em atendimento',
  aguardando_validacao: 'Em conferência', resolvida: 'Concluída', cancelada: 'Arquivada'
};
const gestor = CFG.perfil === 'gestor' || CFG.perfil === 'administrador';
let atual = null, criando = false;
const el = (id) => document.getElementById(id);
const aviso = (mensagem) => {el('aviso').textContent = mensagem || '';};
const campo = (id) => el(id).value;

async function chamar(url, method = 'GET', body) {
  const headers = {'Accept': 'application/json'};
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    headers['X-CSRFToken'] = CFG.csrf;
  }
  const response = await fetch(url, {method, headers, credentials:'same-origin',
                                      body: body === undefined ? undefined : JSON.stringify(body)});
  let result;
  try {result = await response.json();} catch {result = {};}
  if (!response.ok) throw new Error(result.erro || `Falha HTTP ${response.status}`);
  return result;
}

function tornarTexto(tag, texto, classe) {
  const node = document.createElement(tag);
  node.textContent = texto == null ? '' : String(texto);
  if (classe) node.className = classe;
  return node;
}

function card(d) {
  const n = document.createElement('article');
  n.className = 'card';
  n.draggable = true;
  n.tabIndex = 0;
  n.setAttribute('role','button');
  n.setAttribute('aria-label', 'Abrir demanda: ' + d.titulo);
  n.appendChild(tornarTexto('h3',d.titulo));
  n.appendChild(tornarTexto('p',d.area_nome || d.tipo || 'Sem distrito informado'));
  n.appendChild(tornarTexto('span',d.score_origem == null ? 'Pontuação de origem não disponível' :
    'Prioridade: ' + Number(d.score_origem).toFixed(2) + ' / 100', 'badge'));
  n.appendChild(tornarTexto('small',d.cluster_id ? 'ID: ' + d.cluster_id : 'Registro operacional', 'card-code'));
  n.addEventListener('click', () => abrir(d.id));
  n.addEventListener('keydown', e => {if(e.key==='Enter'||e.key===' '){e.preventDefault();abrir(d.id);}});
  n.addEventListener('dragstart', e => {e.dataTransfer.setData('text/plain', d.id); e.dataTransfer.effectAllowed='move';});
  return n;
}

async function carregarEntrada() {
  const alvo = el('entrada-fila');
  if (!alvo) return;
  alvo.replaceChildren();
  try {
    const dados = await chamar(ROTAS.entrada);
    if (!(dados.itens || []).length) {
      alvo.appendChild(tornarTexto('p','Não há cartões novos nas primeiras posições consultadas. Consulte o catálogo para pesquisar outros IDs.'));
      return;
    }
    for (const d of dados.itens) {
      const n = document.createElement('article');
      n.className = 'inbox-card';
      n.appendChild(tornarTexto('small','Posição #' + d.rank + ' · ID: ' + d.cluster_id));
      n.appendChild(tornarTexto('strong',d.titulo));
      n.appendChild(tornarTexto('span','Pontuação calculada: ' + Number(d.score_origem).toFixed(2) + ' / 100','inbox-score'));
      if (gestor) {
        const btn = tornarTexto('button','Iniciar acompanhamento');
        btn.type = 'button';
        btn.className = 'secondary';
        btn.addEventListener('click',async()=>{
          btn.disabled=true;
          try {
            const atualizado = await chamar(ROTAS.acompanhar,'POST',{cluster_id:d.cluster_id});
            await carregar();
            await abrir(atualizado.id);
          } catch(err) { aviso(err.message); btn.disabled=false; }
        });
        n.appendChild(btn);
      } else {
        n.appendChild(tornarTexto('small','Encaminhamento inicial reservado ao gestor.'));
      }
      alvo.appendChild(n);
    }
  } catch(err) {
    alvo.appendChild(tornarTexto('p','Entrada analítica indisponível nesta consulta.'));
  }
}

async function carregar() {
  aviso('');
  try {
    const dados = await chamar(ROTAS.kanban);
    document.querySelectorAll('.column').forEach(c => {
      const estado = c.dataset.status;
      c.querySelector('.count').textContent = dados[estado]?.total ?? 0;
      const lista = c.querySelector('.cards');
      lista.replaceChildren(...(dados[estado]?.itens || []).map(card));
    });
    await carregarEntrada();
  } catch(e) {aviso(e.message);}
}

document.querySelectorAll('.column').forEach(coluna => {
  coluna.addEventListener('dragover', e=>{e.preventDefault();coluna.classList.add('drag-over');});
  coluna.addEventListener('dragleave', ()=>coluna.classList.remove('drag-over'));
  coluna.addEventListener('drop', async e=>{
    e.preventDefault();coluna.classList.remove('drag-over');
    const id=e.dataTransfer.getData('text/plain');
    if(!id)return;
    try{
      const d=await chamar(`${ROTAS.demandas}/${encodeURIComponent(id)}`);
      const destino=coluna.dataset.status;
      if(!PROXIMAS[d.status]?.includes(destino)){aviso('Transição não permitida.');return;}
      if(!gestor&&(destino==='cancelada'||destino==='resolvida'||d.status==='resolvida'||destino==='pendente')){
        aviso('Esta ação exige perfil gestor.');return;
      }
      if(destino==='cancelada'||destino==='resolvida'||d.status==='resolvida'){
        await abrir(id);
        el('novo-status').value=destino;
        el('justificativa').focus();
        return;
      }
      await chamar(`${ROTAS.demandas}/${encodeURIComponent(id)}/status`,'POST',
                   {status:destino,versao:d.versao,justificativa:''});
      await carregar();
    }catch(err){aviso(err.message);}
  });
});

function prazoLocal(iso){
  if(!iso)return '';
  const d=new Date(iso);
  const local=new Date(d.getTime()-d.getTimezoneOffset()*60000);
  return local.toISOString().slice(0,16);
}
function prazoIso(){
  const v=campo('prazo_em');
  return v ? new Date(v).toISOString() : null;
}
function dadosFormulario(){
  return {titulo:campo('titulo'),descricao:campo('descricao'),tipo:campo('tipo'),
          area_nome:campo('area_nome'),prazo_em:prazoIso()};
}
function transicoesPermitidas(status){
  return (PROXIMAS[status] || []).filter(destino => gestor ||
    (destino!=='resolvida'&&destino!=='cancelada'&&destino!=='pendente'&&status!=='resolvida'));
}
function preencher(d){
  el('modal-erro').textContent='';
  el('titulo').value=d?.titulo||'';
  el('descricao').value=d?.descricao||'';
  el('tipo').value=d?.tipo||'';
  el('area_nome').value=d?.area_nome||'';
  el('prazo_em').value=prazoLocal(d?.prazo_em);
  el('justificativa').value='';
  el('dados-origem').textContent=d ?
    `Origem: ${d.origem} · ID: ${d.cluster_id||d.id} · Pontuação na entrada: ${d.score_origem == null ? 'não calculada' : Number(d.score_origem).toFixed(2) + ' / 100'} · Versão: ${d.versao}`:
    'Nova demanda manual, aguardando triagem.';
  el('modal-titulo').textContent=d?`Acompanhamento · ${LABELS[d.status]}`:'Registro demonstrativo';
  const sel=el('novo-status');sel.replaceChildren();
  for(const s of d?transicoesPermitidas(d.status):[]){
    const option=document.createElement('option');option.value=s;option.textContent=LABELS[s];sel.appendChild(option);
  }
  sel.disabled=sel.options.length===0;
  el('btn-transicao').disabled=!d||!sel.options.length;
  el('btn-transicao').hidden=!d;
  el('btn-salvar').disabled=true;
  el('btn-salvar').textContent=d?'Salvar alterações':'Criar demanda';
  el('historico').replaceChildren();
  for(const field of ['titulo','descricao','tipo','area_nome','prazo_em']){
    el(field).disabled=true;
  }
}
async function abrir(id){
  try{
    criando=false;
    atual=await chamar(`${ROTAS.demandas}/${encodeURIComponent(id)}`);
    preencher(atual);
    const h=await chamar(`${ROTAS.demandas}/${encodeURIComponent(id)}/historico`);
    el('historico').appendChild(tornarTexto('h3','Histórico de atividades'));
    for(const ev of h){
      const data=new Date(ev.ocorrido_em).toLocaleString('pt-BR');
      el('historico').appendChild(tornarTexto('p',
        `${data} · ${ev.autor_id} · ${ev.tipo_evento} · ${ev.status_anterior||'—'} → ${ev.status_novo}${ev.justificativa?' · '+ev.justificativa:''}`));
    }
    el('detalhe').showModal();
  }catch(e){aviso(e.message);}
}

el('btn-nova').addEventListener('click',()=>{
  if(!gestor)return;
  criando=true;atual=null;preencher(null);el('detalhe').showModal();
});
el('btn-nova').hidden=true;
el('btn-importar').hidden=true;
el('btn-importar').addEventListener('click',()=>{
  el('cluster-id').value='';
  el('importar-erro').textContent='';
  el('importar-modal').showModal();
  el('cluster-id').focus();
});
el('confirmar-importar').addEventListener('click',async()=>{
  const cid=campo('cluster-id').trim();
  if(!cid){el('importar-erro').textContent='Informe o cluster_id.';return;}
  try{
    const d=await chamar(ROTAS.importar,'POST',{cluster_id:cid});
    el('importar-modal').close();
    await carregar();await abrir(d.id);
  }catch(e){el('importar-erro').textContent=e.message;}
});
el('btn-salvar').addEventListener('click',async()=>{
  if(!gestor)return;
  try{
    const dados=dadosFormulario();
    const d=criando ? await chamar(ROTAS.demandas,'POST',dados) :
      await chamar(`${ROTAS.demandas}/${encodeURIComponent(atual.id)}`,'PATCH',
                   {...dados,versao:atual.versao});
    el('detalhe').close();await carregar();await abrir(d.id);
  }catch(e){el('modal-erro').textContent=e.message;}
});
el('btn-transicao').addEventListener('click',async()=>{
  if(!atual)return;
  try{
    await chamar(`${ROTAS.demandas}/${encodeURIComponent(atual.id)}/status`,'POST',
      {status:campo('novo-status'),versao:atual.versao,justificativa:campo('justificativa')});
    el('detalhe').close();await carregar();
  }catch(e){el('modal-erro').textContent=e.message;}
});
carregar();

const abrirId = new URLSearchParams(location.search).get('abrir');
if (abrirId && /^[a-f0-9-]{36}$/.test(abrirId)) abrir(abrirId);
