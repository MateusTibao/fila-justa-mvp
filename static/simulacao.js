'use strict';
// Demonstração visual: armazenamento apenas nesta sessão do navegador.
// Nenhuma chamada de escrita ao servidor ou à base operacional.
const toggle = document.getElementById('alternar-demo');
if (toggle) {
  let ligado = false;
  const nota = document.getElementById('demo-nota');
  const controles = [...document.querySelectorAll('.demo-control')];
  const prefixo = 'fj-demo-';
  function renderizar() {
    toggle.setAttribute('aria-pressed', String(ligado));
    toggle.textContent = ligado ? 'Encerrar simulação' : 'Ativar simulação de acompanhamento';
    nota.hidden = !ligado;
    controles.forEach(c => {
      c.hidden = !ligado;
      const cartao = c.closest('[data-cluster]');
      const chave = prefixo + cartao.dataset.cluster;
      const seletor = c.querySelector('select');
      const salvo = sessionStorage.getItem(chave) || '';
      seletor.value = salvo;
      c.querySelector('.demo-resultado').textContent = salvo ? 'Simulação local: ' + salvo : '';
    });
  }
  toggle.addEventListener('click', () => { ligado = !ligado; renderizar(); });
  controles.forEach(c => c.querySelector('select').addEventListener('change', e => {
    const chave = prefixo + c.closest('[data-cluster]').dataset.cluster;
    if (e.target.value) sessionStorage.setItem(chave, e.target.value);
    else sessionStorage.removeItem(chave);
    c.querySelector('.demo-resultado').textContent =
      e.target.value ? 'Simulação local: ' + e.target.value : '';
  }));
  renderizar();
}
