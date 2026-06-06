/* =====================================================
   SISTEMA DE INGRESSOS — app.js
   Conecta à API (api.py) → MySQL + SQS
   ===================================================== */

'use strict';

const API_BASE = window.location.origin;

/* ─── CLIENTE HTTP ─────────────────────────────────── */
async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Erro HTTP ${res.status}`);
  }
  return data;
}

/* ─── CADASTRO DE USUÁRIO (PÚBLICO) ───────────────────────────────── */
function openRegisterModal() {
  document.getElementById('registerForm')?.reset();
  document.getElementById('registerInfo').style.display = 'none';
  openModal('registerModal');
}

async function submitRegisterForm(e) {
  e.preventDefault();
  const nome = document.getElementById('regNome').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const senha = document.getElementById('regSenha').value;
  const infoEl = document.getElementById('registerInfo');
  const btn = document.getElementById('btnRegisterSubmit');

  if (!nome || !email || !senha) {
    showToast('Preencha nome, e-mail e senha.', 'error');
    return;
  }

  setBtnLoading(btn, true, 'Enviando...');
  if (infoEl) { infoEl.style.display = 'block'; infoEl.textContent = 'Enviando cadastro para processamento...'; }

  try {
    const payload = { operacao: 'Cadastro', nome, email, senha, admin: 0 };
    await api.sqsUsuario(payload);
    closeModal('registerModal');
    showToast('Cadastro enviado. Aguarde confirmação do sistema.', 'success');
    // Limpar campos
    document.getElementById('regNome').value = '';
    document.getElementById('regEmail').value = '';
    document.getElementById('regSenha').value = '';
  } catch (err) {
    showToast(err.message || 'Erro ao enviar cadastro.', 'error');
  } finally {
    setBtnLoading(btn, false);
    if (infoEl) infoEl.style.display = 'none';
  }
}


const api = {
  health:       () => apiFetch('/api/health'),
  login:        (email, senha) => apiFetch('/api/login', { method: 'POST', body: JSON.stringify({ email, senha }) }),
  getIngressos: () => apiFetch('/api/ingressos'),
  getIngresso:  (id) => apiFetch(`/api/ingressos/${id}`),
  getUsuarios:  () => apiFetch('/api/usuarios'),
  getPedidos:   () => apiFetch('/api/pedidos'),
  getPedidosUsuario: (id) => apiFetch(`/api/pedidos/usuario/${id}`),
  getStats:     () => apiFetch('/api/stats'),
  sqsPedido:    (payload) => apiFetch('/api/sqs/pedidos', { method: 'POST', body: JSON.stringify(payload) }),
  sqsUsuario:   (payload) => apiFetch('/api/sqs/usuarios', { method: 'POST', body: JSON.stringify(payload) }),
  sqsIngresso:  (payload) => apiFetch('/api/sqs/ingressos', { method: 'POST', body: JSON.stringify(payload) }),
};

/* ─── CACHE LOCAL (dados lidos do banco) ───────────── */
const cache = {
  ingressos: [],
  pedidos: [],
  usuarios: [],
  stats: null,
};

/* ─── ESTADO DA APLICAÇÃO ─────────────────────────── */
const USER_STORAGE_KEY = 'ticketflow_current_user';

const App = {
  currentUser: null,
  currentPage: 'login',
  loading: false,

  setUser(user) { this.currentUser = user; },
  clearUser()   { this.currentUser = null; },
  isAdmin()     { return this.currentUser?.tipo === 1; },
};

function saveUserCache(user) {
  try {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  } catch (err) {
    console.warn('Não foi possível salvar usuário no cache:', err);
  }
}

function loadUserCache() {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    if (!raw) return null;
    const user = JSON.parse(raw);
    return user && user.id_usuario ? user : null;
  } catch {
    return null;
  }
}

function clearUserCache() {
  try {
    localStorage.removeItem(USER_STORAGE_KEY);
  } catch {
    // ignore
  }
}

async function restoreSession() {
  const cachedUser = loadUserCache();
  if (!cachedUser) return false;

  App.setUser(cachedUser);
  showToast(`Sessão restaurada: ${cachedUser.nome.split(' ')[0]}`, 'info');

  try {
    if (App.isAdmin()) {
      await loadAdminPanel();
      showPage('admin-panel');
    } else {
      await loadClientPanel();
      showPage('client-panel');
    }
    return true;
  } catch (err) {
    clearUserCache();
    return false;
  }
}

/* ─── ROTEADOR DE PÁGINAS ─────────────────────────── */
function showPage(pageId) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const target = document.getElementById(pageId);
  if (target) {
    target.classList.add('active');
    App.currentPage = pageId;
  }
}

/* ─── UTILITÁRIOS ─────────────────────────────────── */
const fmt = {
  currency: (v) => `R$ ${Number(v).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.')}`,
  date: (d) => {
    if (!d) return '—';
    return new Date(d + (d.includes('T') ? '' : 'T00:00:00')).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' });
  },
  method: (m) => ({ credito: 'Cartão', boleto: 'Boleto', pix: 'PIX', PIX: 'PIX' }[(m || '').toLowerCase()] || m),
};

function calcularTotal(preco, quantidade) {
  const subtotal = Number(preco) * Number(quantidade);
  const taxa = subtotal * 0.10;
  return { subtotal, taxa, total: subtotal + taxa };
}

function formatarCpf(value) {
  const digits = value.replace(/\D/g, '').slice(0, 11);
  return digits
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d)/, '$1.$2')
    .replace(/(\d{3})(\d{1,2})$/, '$1-$2');
}

function formatarCartao(value) {
  const digits = value.replace(/\D/g, '').slice(0, 16);
  return digits.replace(/(\d{4})(?=\d)/g, '$1 ').trim();
}

function formatarValidade(value) {
  const digits = value.replace(/\D/g, '').slice(0, 4);
  if (digits.length <= 2) return digits;
  return `${digits.slice(0, 2)}/${digits.slice(2)}`;
}

function validarCpf(cpf) {
  const digits = cpf.replace(/\D/g, '');
  return digits.length === 11;
}

function togglePagamentoPanels() {
  const metodo = document.getElementById('compraPagamento').value;
  document.querySelectorAll('.pagamento-panel').forEach((panel) => {
    panel.classList.toggle('hidden', panel.dataset.metodo !== metodo);
  });
  const errEl = document.getElementById('pagamentoErro');
  if (errEl) errEl.style.display = 'none';
  updateCreditoResumo();
}

function updateCreditoResumo() {
  const resumo = document.getElementById('pgtoCreditoResumo');
  if (!resumo) return;

  const id = parseInt(document.getElementById('compraIngressoId').value, 10);
  const qtd = parseInt(document.getElementById('compraQtd').value, 10) || 1;
  const ing = getIngressoById(id);
  if (!ing) {
    resumo.textContent = '';
    return;
  }

  const parcelas = parseInt(document.getElementById('pgtoCartaoParcelas')?.value, 10) || 1;
  const { total } = calcularTotal(ing.preco, qtd);
  const parcela = total / parcelas;
  resumo.textContent = `${parcelas}x de ${fmt.currency(parcela)} — Total: ${fmt.currency(total)}`;
}

function limparCamposPagamento() {
  ['pgtoPixCpf', 'pgtoCartaoNumero', 'pgtoCartaoNome', 'pgtoCartaoValidade',
    'pgtoCartaoCvv', 'pgtoBoletoNome', 'pgtoBoletoCpf'].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const parcelas = document.getElementById('pgtoCartaoParcelas');
  if (parcelas) parcelas.value = '1';
  const errEl = document.getElementById('pagamentoErro');
  if (errEl) errEl.style.display = 'none';
}

function coletarDadosPagamento(tipo) {
  const errEl = document.getElementById('pagamentoErro');
  const falhar = (msg) => {
    if (errEl) {
      errEl.textContent = msg;
      errEl.style.display = 'flex';
    }
    return { ok: false, error: msg };
  };

  if (tipo === 'pix') {
    const cpf = document.getElementById('pgtoPixCpf').value;
    if (!validarCpf(cpf)) return falhar('Informe um CPF válido (11 dígitos) para o PIX.');
    return {
      ok: true,
      dados: { cpf_pagador: cpf.replace(/\D/g, '') },
    };
  }

  if (tipo === 'credito') {
    const numero = document.getElementById('pgtoCartaoNumero').value.replace(/\s/g, '');
    const nome = document.getElementById('pgtoCartaoNome').value.trim();
    const validade = document.getElementById('pgtoCartaoValidade').value.trim();
    const cvv = document.getElementById('pgtoCartaoCvv').value.trim();
    const parcelas = parseInt(document.getElementById('pgtoCartaoParcelas').value, 10) || 1;

    if (numero.length !== 16 || !/^\d+$/.test(numero)) {
      return falhar('Número do cartão inválido (16 dígitos).');
    }
    if (!nome) return falhar('Informe o nome impresso no cartão.');
    if (!/^\d{2}\/\d{2}$/.test(validade)) {
      return falhar('Validade inválida. Use o formato MM/AA.');
    }
    if (!/^\d{3,4}$/.test(cvv)) return falhar('CVV inválido (3 ou 4 dígitos).');
    if (parcelas < 1 || parcelas > 12) return falhar('Parcelas deve ser entre 1 e 12.');

    return {
      ok: true,
      dados: {
        parcelas,
        nome_titular: nome,
        validade,
        cartao_final: numero.slice(-4),
      },
    };
  }

  if (tipo === 'boleto') {
    const nome = document.getElementById('pgtoBoletoNome').value.trim();
    const cpf = document.getElementById('pgtoBoletoCpf').value;
    if (!nome) return falhar('Informe o nome completo para o boleto.');
    if (!validarCpf(cpf)) return falhar('Informe um CPF válido para o boleto.');
    return {
      ok: true,
      dados: {
        nome_pagador: nome,
        cpf: cpf.replace(/\D/g, ''),
      },
    };
  }

  return falhar('Forma de pagamento inválida.');
}

function setBtnLoading(btn, loading, label = 'Processando...') {
  if (!btn) return;
  if (loading) {
    btn.dataset.originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = label;
  } else {
    btn.disabled = false;
    if (btn.dataset.originalText) btn.textContent = btn.dataset.originalText;
  }
}

function showToast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type]}</span><span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

/* ─── CARREGAMENTO DE DADOS ───────────────────────── */
async function loadIngressos() {
  const data = await api.getIngressos();
  cache.ingressos = data.ingressos || [];
  return cache.ingressos;
}

async function loadPedidosUsuario(usuarioId) {
  const data = await api.getPedidosUsuario(usuarioId);
  return data.pedidos || [];
}

async function loadAllPedidos() {
  const data = await api.getPedidos();
  cache.pedidos = data.pedidos || [];
  return cache.pedidos;
}

async function loadUsuarios() {
  const data = await api.getUsuarios();
  cache.usuarios = data.usuarios || [];
  return cache.usuarios;
}

async function loadStats() {
  const data = await api.getStats();
  cache.stats = data.stats;
  return cache.stats;
}

function getIngressoById(id) {
  return cache.ingressos.find(i => i.id_ingresso === id) || null;
}

/* ─── STATUS DA API ───────────────────────────────── */
async function checkApiHealth() {
  const el = document.getElementById('apiStatus');
  if (!el) return;
  try {
    const health = await api.health();
    if (health.ok) {
      el.textContent = '● API conectada ao banco';
      el.className = 'api-status online';
    } else {
      el.textContent = `● Banco indisponível${health.database_error ? ': ' + health.database_error : ''}`;
      el.className = 'api-status offline';
    }
  } catch {
    el.textContent = '● API offline — execute python api.py';
    el.className = 'api-status offline';
  }
}

/* ─── LOGIN ───────────────────────────────────────── */
async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('loginEmail').value.trim();
  const senha = document.getElementById('loginSenha').value;
  const errEl = document.getElementById('loginError');
  const btn = document.querySelector('#loginForm button[type="submit"]');

  setBtnLoading(btn, true, 'Entrando...');
  errEl.style.display = 'none';

  try {
    const data = await api.login(email, senha);
    const user = data.user;

    App.setUser(user);
    showToast(`Bem-vindo, ${user.nome.split(' ')[0]}!`, 'success');

    if (App.isAdmin()) {
      await loadAdminPanel();
      showPage('admin-panel');
    } else {
      await loadClientPanel();
      showPage('client-panel');
    }

    saveUserCache(user);
  } catch (err) {
    errEl.textContent = err.message || 'E-mail ou senha incorretos.';
    errEl.style.display = 'flex';
    document.getElementById('loginSenha').value = '';
  } finally {
    setBtnLoading(btn, false);
  }
}

function handleLogout() {
  App.clearUser();
  clearUserCache();
  document.getElementById('loginEmail').value = '';
  document.getElementById('loginSenha').value = '';
  document.getElementById('loginError').style.display = 'none';
  showPage('login');
  showToast('Sessão encerrada.', 'info');
}

async function refreshClientState() {
  if (!App.currentUser) return;
  await loadIngressos();
  renderIngressosDisponiveis();
  await renderMeusPedidos();
  if (App.currentPage === 'client-panel') {
    togglePagamentoPanels();
    renderContaCliente();
  }
}

/* ─── PAINEL DO CLIENTE ──────────────────────────── */
async function loadClientPanel() {
  const user = App.currentUser;
  document.getElementById('clientUserName').textContent = user.nome.split(' ')[0];

  try {
    await loadIngressos();
    renderIngressosDisponiveis();
    await renderMeusPedidos();
  } catch (err) {
    showToast(`Erro ao carregar dados: ${err.message}`, 'error');
  }
}

function renderIngressosDisponiveis(search = '') {
  const grid = document.getElementById('ingressosGrid');
  let ingressos = [...cache.ingressos];

  if (search) {
    ingressos = ingressos.filter(i => i.nome.toLowerCase().includes(search.toLowerCase()));
  }

  if (!ingressos.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-icon">🔍</div>
      <h3>Nenhum ingresso encontrado</h3>
      <p>${search ? 'Tente outros termos de busca.' : 'Não há eventos cadastrados no banco.'}</p>
    </div>`;
    return;
  }

  grid.innerHTML = ingressos.map(ing => `
    <div class="ingresso-card" onclick="openCompraModal(${ing.id_ingresso})">
      <div class="ingresso-banner">
        <div class="event-icon">${ing.emoji}</div>
        <span class="ingresso-status ${ing.quantidade > 0 ? 'disponivel' : 'esgotado'}">
          ${ing.quantidade > 0 ? '● Disponível' : '✕ Esgotado'}
        </span>
      </div>
      <div class="ingresso-body">
        <div class="ingresso-event-name">${ing.nome}</div>
        <div class="ingresso-meta">
          <span>📅 ${fmt.date(ing.data)}</span>
          <span>🎟 ${ing.quantidade > 0 ? `${ing.quantidade} restantes` : 'Sem estoque'}</span>
        </div>
      </div>
      <div class="ingresso-footer">
        <div class="ingresso-price">${fmt.currency(ing.preco)}</div>
        ${ing.quantidade > 0
          ? `<button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); openCompraModal(${ing.id_ingresso})">Comprar</button>`
          : `<span class="badge badge-error">Esgotado</span>`
        }
      </div>
    </div>
  `).join('');
}

async function renderMeusPedidos() {
  const container = document.getElementById('meusPedidosLista');

  try {
    const pedidos = await loadPedidosUsuario(App.currentUser.id_usuario);

    if (!pedidos.length) {
      container.innerHTML = `<div class="empty-state">
        <div class="empty-icon">🎟</div>
        <h3>Você ainda não tem ingressos</h3>
        <p>Explore os eventos disponíveis e faça sua compra.</p>
      </div>`;
      return;
    }

    container.innerHTML = pedidos.map(p => `
      <div class="ticket-item">
        <div class="ticket-icon">${p.ingresso_emoji}</div>
        <div class="ticket-info">
          <div class="ticket-name">${p.ingresso_nome}</div>
          <div class="ticket-meta">
            ${fmt.method(p.tipo_pagamento)} · Qtd: ${p.quantidade}
          </div>
        </div>
        <div style="text-align:right">
          <div class="ticket-price">${fmt.currency(p.valor_total)}</div>
          <span class="badge badge-success mt-1">Confirmado</span>
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><p>Erro ao carregar pedidos: ${err.message}</p></div>`;
  }
}

function openCompraModal(id_ingresso) {
  const ing = getIngressoById(id_ingresso);
  if (!ing || ing.quantidade === 0) {
    showToast('Ingresso indisponível.', 'error');
    return;
  }

  document.getElementById('compraModalTitle').textContent = ing.nome;
  document.getElementById('compraIngressoId').value = id_ingresso;
  document.getElementById('compraIngressoNome').textContent = ing.nome;
  document.getElementById('compraIngressoData').textContent = fmt.date(ing.data);
  document.getElementById('compraIngressoPreco').textContent = fmt.currency(ing.preco);
  document.getElementById('compraQtd').value = 1;
  document.getElementById('compraQtd').max = Math.min(ing.quantidade, 10);
  document.getElementById('compraPagamento').value = 'pix';
  limparCamposPagamento();
  const boletoNome = document.getElementById('pgtoBoletoNome');
  if (boletoNome && App.currentUser) boletoNome.value = App.currentUser.nome;
  togglePagamentoPanels();
  updateCompraTotal();
  openModal('compraModal');
}

function updateCompraTotal() {
  const id = parseInt(document.getElementById('compraIngressoId').value, 10);
  const qtd = parseInt(document.getElementById('compraQtd').value, 10) || 1;
  const ing = getIngressoById(id);
  if (!ing) return;

  const { subtotal, taxa, total } = calcularTotal(ing.preco, qtd);
  document.getElementById('compraSubtotal').textContent = fmt.currency(subtotal);
  document.getElementById('compraTaxa').textContent = fmt.currency(taxa);
  document.getElementById('compraTotal').textContent = fmt.currency(total);
  updateCreditoResumo();
}

async function handleCompra() {
  const btn = document.getElementById('btnConfirmarCompra');
  const id = parseInt(document.getElementById('compraIngressoId').value, 10);
  const qtd = parseInt(document.getElementById('compraQtd').value, 10) || 1;
  const pagamento = document.getElementById('compraPagamento').value;
  const ing = getIngressoById(id);

  if (!ing || !App.currentUser) {
    showToast('Sessão inválida. Faça login novamente.', 'error');
    return;
  }

  const { total } = calcularTotal(ing.preco, qtd);
  const pgto = coletarDadosPagamento(pagamento);
  if (!pgto.ok) {
    showToast(pgto.error, 'error');
    return;
  }

  setBtnLoading(btn, true, 'Enviando para SQS...');

  try {
    const result = await api.sqsPedido({
      usuario_id: App.currentUser.id_usuario,
      ingresso_id: id,
      quantidade: qtd,
      tipo_pagamento: pagamento,
      valor_total: total,
      pagamento: pgto.dados,
    });

    closeModal('compraModal');
    showToast(`Pedido enviado para fila SQS — ${ing.nome} (${qtd}x)`, 'success');
    console.log('Payload SQS:', result.payload);

    await refreshClientState();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    setBtnLoading(btn, false);
  }
}

/* ─── PAINEL DO ADMINISTRADOR ────────────────────── */
async function loadAdminPanel() {
  const user = App.currentUser;
  document.getElementById('adminUserName').textContent = user.nome.split(' ')[0];

  try {
    await Promise.all([loadStats(), loadIngressos(), loadUsuarios(), loadAllPedidos()]);
    loadAdminStats();
    loadAdminTab('ingressos');
  } catch (err) {
    showToast(`Erro ao carregar painel: ${err.message}`, 'error');
  }
}

function loadAdminStats() {
  const s = cache.stats;
  if (!s) return;
  document.getElementById('statUsuarios').textContent = s.totalUsuarios;
  document.getElementById('statIngressos').textContent = s.totalIngressos;
  document.getElementById('statPedidos').textContent = s.pedidosAprovados;
  document.getElementById('statReceita').textContent = fmt.currency(s.receita);
}

function loadAdminTab(tab) {
  document.querySelectorAll('#adminPanel .tab-btn, #adminTabs .tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });

  const content = document.getElementById('adminTabContent');

  if (tab === 'ingressos') {
    const ingressos = cache.ingressos;
    content.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">Ingressos</div>
          <div class="section-subtitle">Gerenciamento de eventos — escrita via fila SQS</div>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="openIngressoForm('Cadastro')">+ Novo Ingresso</button>
      </div>
      <div class="alert alert-info">
        ℹ️ Cadastro, edição e exclusão são enviados para a fila <strong>SQS de Ingressos</strong> e processados pelo serviço de processamento.
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr><th>ID</th><th>Evento</th><th>Data</th><th>Preço</th><th>Quantidade</th><th>Status</th><th>Ações</th></tr>
          </thead>
          <tbody>
            ${ingressos.map(i => `
              <tr>
                <td class="mono text-muted">#${String(i.id_ingresso).padStart(3, '0')}</td>
                <td><div style="display:flex;align-items:center;gap:0.5rem"><span>${i.emoji}</span><span style="font-weight:500">${i.nome}</span></div></td>
                <td class="text-muted">${fmt.date(i.data)}</td>
                <td class="text-accent mono">${fmt.currency(i.preco)}</td>
                <td><span class="badge ${i.quantidade > 0 ? 'badge-success' : 'badge-error'}">${i.quantidade > 0 ? `${i.quantidade} disp.` : 'Esgotado'}</span></td>
                <td><span class="badge ${i.quantidade > 0 ? 'badge-info' : 'badge-muted'}">${i.quantidade > 0 ? 'Ativo' : 'Inativo'}</span></td>
                <td>
                  <div class="flex gap-1">
                    <button class="btn btn-ghost btn-sm" onclick='openIngressoForm("Edicao", ${JSON.stringify(i)})'>✏ Editar</button>
                    <button class="btn btn-danger btn-sm" onclick="excluirIngresso(${i.id_ingresso}, '${i.nome.replace(/'/g, "\\'")}')">✕</button>
                  </div>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>`;
  }

  else if (tab === 'pedidos') {
    const pedidos = cache.pedidos;
    content.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">Pedidos</div>
          <div class="section-subtitle">Histórico de compras no banco (RDS)</div>
        </div>
        <div class="flex gap-1 items-center">
          <span class="badge badge-info">Via SQS</span>
          <span class="badge badge-muted">${pedidos.length} pedidos</span>
        </div>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr><th>ID</th><th>Usuário</th><th>Ingresso</th><th>Pagamento</th><th>Qtd</th><th>Total</th><th>Status</th></tr>
          </thead>
          <tbody>
            ${pedidos.length ? pedidos.map(p => `
              <tr>
                <td class="mono text-muted">#${String(p.id_pedido).padStart(3, '0')}</td>
                <td>${p.usuario_nome}</td>
                <td><div style="display:flex;align-items:center;gap:0.4rem"><span>${p.ingresso_emoji}</span><span>${p.ingresso_nome}</span></div></td>
                <td><span class="badge badge-muted">${fmt.method(p.tipo_pagamento)}</span></td>
                <td class="mono">${p.quantidade}x</td>
                <td class="text-accent mono">${fmt.currency(p.valor_total)}</td>
                <td><span class="badge badge-success">Confirmado</span></td>
              </tr>
            `).join('') : '<tr><td colspan="7" class="text-muted">Nenhum pedido registrado.</td></tr>'}
          </tbody>
        </table>
      </div>`;
  }

  else if (tab === 'usuarios') {
    const usuarios = cache.usuarios;
    content.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">Usuários</div>
          <div class="section-subtitle">Cadastro via fila SQS de Usuários</div>
        </div>
        <button class="btn btn-secondary btn-sm" onclick="openUsuarioForm('Cadastro')">+ Novo Usuário</button>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr><th>ID</th><th>Nome</th><th>E-mail</th><th>Tipo</th><th>Ações</th></tr>
          </thead>
          <tbody>
            ${usuarios.map(u => `
              <tr>
                <td class="mono text-muted">#${String(u.id_usuario).padStart(3, '0')}</td>
                <td style="font-weight:500">${u.nome}</td>
                <td class="text-muted">${u.email}</td>
                <td><span class="badge ${u.tipo === 1 ? 'badge-warning' : 'badge-info'}">${u.tipo === 1 ? '⚙ Admin' : '👤 Usuário'}</span></td>
                <td>
                  <div class="flex gap-1">
                    <button class="btn btn-ghost btn-sm" onclick='openUsuarioForm("Edicao", ${JSON.stringify(u)})'>✏ Editar</button>
                    <button class="btn btn-danger btn-sm" onclick="excluirUsuario(${u.id_usuario}, '${u.nome.replace(/'/g, "\\'")}')">✕</button>
                  </div>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>`;
  }

  else if (tab === 'dashboard') {
    const stats = cache.stats || {};
    content.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">Dashboard</div>
          <div class="section-subtitle">Visão geral do sistema</div>
        </div>
      </div>
      <div class="stats-grid" style="grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin-bottom: 2rem">
        <div class="stat-card">
          <div class="stat-label">Total de Pedidos</div>
          <div class="stat-value">${stats.totalPedidos || 0}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">Ingressos Disponíveis</div>
          <div class="stat-value">${stats.ingressosDisponiveis || 0}</div>
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem">
        <div class="card">
          <div class="card-header"><span class="card-title">Fluxo AWS</span><span class="badge badge-info">Arquitetura</span></div>
          <div style="font-size:0.85rem; color: var(--text-muted); line-height: 2">
            <div>🌐 <strong style="color:var(--text)">Web (EC2)</strong> → API Flask</div>
            <div>📦 <strong style="color:var(--text)">SQS Pedidos</strong> → Checkout / Pagamento</div>
            <div>✅ <strong style="color:var(--text)">SQS Processamento</strong> → RDS MySQL</div>
            <div>📊 <strong style="color:var(--text)">RDS</strong> → Leitura em tempo real</div>
          </div>
        </div>
        <div class="card">
          <div class="card-header"><span class="card-title">Tabelas do Banco</span><span class="badge badge-muted">MySQL</span></div>
          <div style="font-size:0.82rem; color: var(--text-muted); line-height:2">
            <div>👤 usuarios — ${stats.totalUsuarios || 0}</div>
            <div>🎟 ingressos — ${stats.totalIngressos || 0}</div>
            <div>🛒 pedidos — ${stats.totalPedidos || 0}</div>
            <div style="margin-top:0.5rem; padding-top:0.5rem; border-top: 1px solid var(--border)">
              💰 Receita: <span class="text-accent mono">${fmt.currency(stats.receita || 0)}</span>
            </div>
          </div>
        </div>
      </div>`;
  }
}

/* ─── FORMULÁRIOS ADMIN → SQS ───────────────────── */
function openIngressoForm(operacao, ingresso = null) {
  document.getElementById('ingressoFormOperacao').value = operacao;
  document.getElementById('ingressoFormId').value = ingresso?.id_ingresso || '';
  document.getElementById('ingressoFormNome').value = ingresso?.nome || '';
  document.getElementById('ingressoFormData').value = ingresso?.data?.slice(0, 10) || '';
  document.getElementById('ingressoFormValor').value = ingresso?.preco ?? '';
  document.getElementById('ingressoFormQtd').value = ingresso?.quantidade ?? '';
  document.getElementById('ingressoModalTitle').textContent =
    operacao === 'Cadastro' ? 'Novo Ingresso' : 'Editar Ingresso';
  openModal('ingressoModal');
}

async function submitIngressoForm(e) {
  e.preventDefault();
  const btn = document.getElementById('btnIngressoSubmit');
  const operacao = document.getElementById('ingressoFormOperacao').value;

  const payload = {
    operacao,
    nome: document.getElementById('ingressoFormNome').value.trim(),
    data: document.getElementById('ingressoFormData').value,
    valor: parseFloat(document.getElementById('ingressoFormValor').value),
    quantidade: parseInt(document.getElementById('ingressoFormQtd').value, 10),
  };

  if (operacao !== 'Cadastro') {
    payload.ingresso_id = parseInt(document.getElementById('ingressoFormId').value, 10);
  }

  setBtnLoading(btn, true);
  try {
    await api.sqsIngresso(payload);
    closeModal('ingressoModal');
    showToast(`Ingresso enviado para SQS (${operacao})`, 'success');
    setTimeout(async () => {
      await loadIngressos();
      loadAdminTab('ingressos');
      loadStats().then(loadAdminStats);
    }, 2000);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    setBtnLoading(btn, false);
  }
}

async function excluirIngresso(id, nome) {
  if (!confirm(`Excluir ingresso "${nome}"? A mensagem será enviada para a fila SQS.`)) return;
  try {
    await api.sqsIngresso({ operacao: 'Exclusao', ingresso_id: id });
    showToast('Exclusão enviada para SQS', 'success');
    setTimeout(async () => {
      await loadIngressos();
      loadAdminTab('ingressos');
    }, 2000);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function openUsuarioForm(operacao, usuario = null) {
  document.getElementById('usuarioFormOperacao').value = operacao;
  document.getElementById('usuarioFormId').value = usuario?.id_usuario || '';
  document.getElementById('usuarioFormNome').value = usuario?.nome || '';
  document.getElementById('usuarioFormEmail').value = usuario?.email || '';
  document.getElementById('usuarioFormSenha').value = '';
  document.getElementById('usuarioFormAdmin').value = String(usuario?.tipo ?? 0);
  document.getElementById('usuarioModalTitle').textContent =
    operacao === 'Cadastro' ? 'Novo Usuário' : 'Editar Usuário';
  openModal('usuarioModal');
}

async function submitUsuarioForm(e) {
  e.preventDefault();
  const btn = document.getElementById('btnUsuarioSubmit');
  const operacao = document.getElementById('usuarioFormOperacao').value;

  const payload = {
    operacao,
    nome: document.getElementById('usuarioFormNome').value.trim(),
    email: document.getElementById('usuarioFormEmail').value.trim(),
    senha: document.getElementById('usuarioFormSenha').value,
    admin: parseInt(document.getElementById('usuarioFormAdmin').value, 10),
  };

  if (operacao !== 'Cadastro') {
    payload.usuario_id = parseInt(document.getElementById('usuarioFormId').value, 10);
  }
  if (!payload.senha) delete payload.senha;

  if (operacao === 'Cadastro' && !document.getElementById('usuarioFormSenha').value) {
    showToast('Senha é obrigatória no cadastro.', 'error');
    return;
  }

  setBtnLoading(btn, true);
  try {
    await api.sqsUsuario(payload);
    closeModal('usuarioModal');
    showToast(`Usuário enviado para SQS (${operacao})`, 'success');
    setTimeout(async () => {
      await loadUsuarios();
      loadAdminTab('usuarios');
      loadStats().then(loadAdminStats);
    }, 2000);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    setBtnLoading(btn, false);
  }
}

async function excluirUsuario(id, nome) {
  if (!confirm(`Excluir usuário "${nome}"? A mensagem será enviada para a fila SQS.`)) return;
  try {
    await api.sqsUsuario({ operacao: 'Exclusao', usuario_id: id });
    showToast('Exclusão enviada para SQS', 'success');
    setTimeout(async () => {
      await loadUsuarios();
      loadAdminTab('usuarios');
    }, 2000);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

/* ─── TABS CLIENT ──────────────────────────────────── */
function loadClientTab(tab) {
  document.querySelectorAll('#clientPanel .tab-btn, #clientMobileTabs .tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });

  const sections = {
    ingressos: document.getElementById('clientIngressos'),
    meus: document.getElementById('clientMeus'),
    conta: document.getElementById('clientConta'),
  };

  Object.entries(sections).forEach(([key, el]) => {
    if (el) el.style.display = key === tab ? 'block' : 'none';
  });

  if (tab === 'conta') renderContaCliente();
  if (tab === 'meus') renderMeusPedidos();
}

async function renderContaCliente() {
  const user = App.currentUser;
  document.getElementById('contaNome').textContent = user.nome;
  document.getElementById('contaEmail').textContent = user.email;

  const tipoEl = document.getElementById('contaTipo');
  if (tipoEl) {
    tipoEl.innerHTML = user.tipo === 1
      ? '<span class="badge badge-warning">⚙ Admin</span>'
      : '<span class="badge badge-info">👤 Usuário</span>';
  }

  try {
    const pedidos = await loadPedidosUsuario(user.id_usuario);
    const total = pedidos.reduce((s, p) => s + p.valor_total, 0);
    document.getElementById('contaTotalGasto').textContent = fmt.currency(total);
    document.getElementById('contaTotalPedidos').textContent = pedidos.length;
  } catch {
    document.getElementById('contaTotalGasto').textContent = '—';
    document.getElementById('contaTotalPedidos').textContent = '—';
  }
}

/* ─── INICIALIZAÇÃO ───────────────────────────────── */
document.addEventListener('DOMContentLoaded', async () => {
  setTimeout(() => {
    const loader = document.getElementById('loaderOverlay');
    if (loader) loader.classList.add('hidden');
    setTimeout(() => loader?.remove(), 500);
  }, 1200);

  if (!(await restoreSession())) {
    showPage('login');
  }
  checkApiHealth();

  const loginForm = document.getElementById('loginForm');
  if (loginForm) loginForm.addEventListener('submit', handleLogin);

  const btnOpenRegister = document.getElementById('btnOpenRegister');
  if (btnOpenRegister) btnOpenRegister.addEventListener('click', openRegisterModal);

  const registerForm = document.getElementById('registerForm');
  if (registerForm) registerForm.addEventListener('submit', submitRegisterForm);

  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.classList.remove('open');
    });
  });

  const searchInput = document.getElementById('clientSearch');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => renderIngressosDisponiveis(e.target.value));
  }

  const compraQtd = document.getElementById('compraQtd');
  if (compraQtd) compraQtd.addEventListener('input', updateCompraTotal);

  const compraPag = document.getElementById('compraPagamento');
  if (compraPag) {
    compraPag.addEventListener('change', () => {
      togglePagamentoPanels();
      updateCompraTotal();
    });
  }

  const pgtoParcelas = document.getElementById('pgtoCartaoParcelas');
  if (pgtoParcelas) pgtoParcelas.addEventListener('change', updateCreditoResumo);

  const pgtoPixCpf = document.getElementById('pgtoPixCpf');
  if (pgtoPixCpf) {
    pgtoPixCpf.addEventListener('input', (e) => {
      e.target.value = formatarCpf(e.target.value);
    });
  }

  const pgtoBoletoCpf = document.getElementById('pgtoBoletoCpf');
  if (pgtoBoletoCpf) {
    pgtoBoletoCpf.addEventListener('input', (e) => {
      e.target.value = formatarCpf(e.target.value);
    });
  }

  const pgtoCartaoNumero = document.getElementById('pgtoCartaoNumero');
  if (pgtoCartaoNumero) {
    pgtoCartaoNumero.addEventListener('input', (e) => {
      e.target.value = formatarCartao(e.target.value);
    });
  }

  const pgtoCartaoValidade = document.getElementById('pgtoCartaoValidade');
  if (pgtoCartaoValidade) {
    pgtoCartaoValidade.addEventListener('input', (e) => {
      e.target.value = formatarValidade(e.target.value);
    });
  }

  const ingressoForm = document.getElementById('ingressoForm');
  if (ingressoForm) ingressoForm.addEventListener('submit', submitIngressoForm);

  const usuarioForm = document.getElementById('usuarioForm');
  if (usuarioForm) usuarioForm.addEventListener('submit', submitUsuarioForm);
});
