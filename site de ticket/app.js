/* =====================================================
   SISTEMA DE INGRESSOS — app.js
   Simula leitura do banco MySQL conforme estrutura
   definida no app.py e no roadmap
   ===================================================== */

'use strict';

/* ─── BANCO DE DADOS SIMULADO (READ-ONLY) ─────────────
   Espelha as tabelas: usuarios, ingressos, pedidos
   Dados de exemplo para demonstração acadêmica
────────────────────────────────────────────────────── */
const DB = {
  usuarios: [
    { id_usuario: 1, nome: 'Ana Souza',     email: 'ana@email.com',    senha: '***', tipo: 1 }, // admin
    { id_usuario: 2, nome: 'João Pereira',  email: 'joao@email.com',   senha: '***', tipo: 0 },
    { id_usuario: 3, nome: 'Carla Melo',    email: 'carla@email.com',  senha: '***', tipo: 0 },
    { id_usuario: 4, nome: 'Rafael Lima',   email: 'rafael@email.com', senha: '***', tipo: 0 },
    { id_usuario: 5, nome: 'Juliana Costa', email: 'ju@email.com',     senha: '***', tipo: 0 },
  ],

  ingressos: [
    { id_ingresso: 1, nome: 'Rock in Rio 2025',    data: '2025-09-20', preco: 450.00, quantidade: 50,  dono: null,     emoji: '🎸' },
    { id_ingresso: 2, nome: 'Lollapalooza BR',     data: '2025-03-28', preco: 380.00, quantidade: 0,   dono: null,     emoji: '🎤' },
    { id_ingresso: 3, nome: 'Festival de Jazz SP', data: '2025-07-12', preco: 120.00, quantidade: 200, dono: null,     emoji: '🎷' },
    { id_ingresso: 4, nome: 'Anime Friends 2025',  data: '2025-07-04', preco: 95.00,  quantidade: 300, dono: null,     emoji: '🎌' },
    { id_ingresso: 5, nome: 'Show Ivete Sangalo',  data: '2025-08-15', preco: 220.00, quantidade: 15,  dono: null,     emoji: '🌟' },
    { id_ingresso: 6, nome: 'Carnaval Premium RJ', data: '2026-03-01', preco: 750.00, quantidade: 80,  dono: null,     emoji: '🎭' },
  ],

  pedidos: [
    { id_pedido: 1, id_usuario: 2, id_ingresso: 3, tipo_pagamento: 'PIX',     quantidade: 2, status: 'aprovado',  data_pedido: '2025-01-10' },
    { id_pedido: 2, id_usuario: 3, id_ingresso: 1, tipo_pagamento: 'credito', quantidade: 1, status: 'aprovado',  data_pedido: '2025-01-12' },
    { id_pedido: 3, id_usuario: 4, id_ingresso: 2, tipo_pagamento: 'boleto',  quantidade: 2, status: 'cancelado', data_pedido: '2025-01-14' },
    { id_pedido: 4, id_usuario: 2, id_ingresso: 5, tipo_pagamento: 'PIX',     quantidade: 1, status: 'pendente',  data_pedido: '2025-01-15' },
    { id_pedido: 5, id_usuario: 5, id_ingresso: 4, tipo_pagamento: 'credito', quantidade: 3, status: 'aprovado',  data_pedido: '2025-01-16' },
  ],

  // Credenciais de login (READ)
  credenciais: [
    { email: 'ana@email.com',   senha: 'admin123', id_usuario: 1 },
    { email: 'joao@email.com',  senha: 'user123',  id_usuario: 2 },
    { email: 'carla@email.com', senha: 'user123',  id_usuario: 3 },
  ]
};

/* ─── FUNÇÕES DE LEITURA DO BANCO ─────────────────── */
const dbRead = {
  /** SELECT * FROM usuarios */
  getAllUsuarios: () => [...DB.usuarios],

  /** SELECT * FROM usuarios WHERE id_usuario = ? */
  getUsuarioById: (id) => DB.usuarios.find(u => u.id_usuario === id) || null,

  /** SELECT * FROM ingressos */
  getAllIngressos: () => [...DB.ingressos],

  /** SELECT * FROM ingressos WHERE id_ingresso = ? */
  getIngressoById: (id) => DB.ingressos.find(i => i.id_ingresso === id) || null,

  /** SELECT * FROM pedidos */
  getAllPedidos: () => [...DB.pedidos],

  /** SELECT p.*, u.nome AS usuario_nome, i.nome AS ingresso_nome
      FROM pedidos p
      JOIN usuarios u ON p.id_usuario = u.id_usuario
      JOIN ingressos i ON p.id_ingresso = i.id_ingresso */
  getPedidosJoined: () => DB.pedidos.map(p => ({
    ...p,
    usuario_nome:  DB.usuarios.find(u => u.id_usuario  === p.id_usuario)?.nome  || 'Desconhecido',
    ingresso_nome: DB.ingressos.find(i => i.id_ingresso === p.id_ingresso)?.nome || 'Desconhecido',
    ingresso_preco:DB.ingressos.find(i => i.id_ingresso === p.id_ingresso)?.preco|| 0,
    ingresso_emoji:DB.ingressos.find(i => i.id_ingresso === p.id_ingresso)?.emoji|| '🎫',
  })),

  /** SELECT * FROM pedidos WHERE id_usuario = ? */
  getPedidosByUsuario: (id_usuario) => dbRead.getPedidosJoined().filter(p => p.id_usuario === id_usuario),

  /** Auth: SELECT * FROM usuarios WHERE email = ? AND senha = ? */
  autenticar: (email, senha) => {
    const cred = DB.credenciais.find(c => c.email === email && c.senha === senha);
    if (!cred) return null;
    return DB.usuarios.find(u => u.id_usuario === cred.id_usuario) || null;
  },

  /** Estatísticas para dashboard */
  getStats: () => ({
    totalUsuarios:  DB.usuarios.length,
    totalIngressos: DB.ingressos.length,
    totalPedidos:   DB.pedidos.length,
    pedidosAprovados: DB.pedidos.filter(p => p.status === 'aprovado').length,
    receita: DB.pedidos
      .filter(p => p.status === 'aprovado')
      .reduce((sum, p) => {
        const ing = DB.ingressos.find(i => i.id_ingresso === p.id_ingresso);
        return sum + (ing ? ing.preco * p.quantidade : 0);
      }, 0),
    ingressosDisponiveis: DB.ingressos.filter(i => i.quantidade > 0).length,
  })
};

/* ─── ESTADO DA APLICAÇÃO ─────────────────────────── */
const App = {
  currentUser: null,
  currentPage: 'login',
  searchTerm: '',
  filterStatus: 'todos',

  setUser(user) { this.currentUser = user; },
  clearUser()   { this.currentUser = null; },
  isAdmin()     { return this.currentUser?.tipo === 1; },
};

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
  date:     (d) => new Date(d + 'T00:00:00').toLocaleDateString('pt-BR', { day:'2-digit', month:'short', year:'numeric' }),
  method:   (m) => ({ credito: 'Cartão', boleto: 'Boleto', PIX: 'PIX' }[m] || m),
};

function showToast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type]}</span><span>${msg}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

function openModal(id)  { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

/* ─── LOGIN ───────────────────────────────────────── */
function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById('loginEmail').value.trim();
  const senha = document.getElementById('loginSenha').value;
  const errEl = document.getElementById('loginError');

  const user = dbRead.autenticar(email, senha);
  if (!user) {
    errEl.textContent = 'E-mail ou senha incorretos.';
    errEl.style.display = 'flex';
    document.getElementById('loginSenha').value = '';
    return;
  }

  errEl.style.display = 'none';
  App.setUser(user);
  showToast(`Bem-vindo, ${user.nome.split(' ')[0]}!`, 'success');

  if (App.isAdmin()) {
    loadAdminPanel();
    showPage('admin-panel');
  } else {
    loadClientPanel();
    showPage('client-panel');
  }
}

function handleLogout() {
  App.clearUser();
  document.getElementById('loginEmail').value = '';
  document.getElementById('loginSenha').value = '';
  document.getElementById('loginError').style.display = 'none';
  showPage('login');
  showToast('Sessão encerrada.', 'info');
}

/* ─── PAINEL DO CLIENTE ──────────────────────────── */
function loadClientPanel() {
  const user = App.currentUser;

  // Atualizar navbar
  document.getElementById('clientUserName').textContent = user.nome.split(' ')[0];

  // Carregar ingressos disponíveis
  renderIngressosDisponiveis();

  // Carregar meus ingressos
  renderMeusPedidos();
}

function renderIngressosDisponiveis(search = '') {
  const grid = document.getElementById('ingressosGrid');
  let ingressos = dbRead.getAllIngressos();

  if (search) {
    ingressos = ingressos.filter(i =>
      i.nome.toLowerCase().includes(search.toLowerCase())
    );
  }

  if (!ingressos.length) {
    grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">
      <div class="empty-icon">🔍</div>
      <h3>Nenhum ingresso encontrado</h3>
      <p>Tente outros termos de busca.</p>
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

function renderMeusPedidos() {
  const container = document.getElementById('meusPedidosLista');
  const pedidos = dbRead.getPedidosByUsuario(App.currentUser.id_usuario);

  if (!pedidos.length) {
    container.innerHTML = `<div class="empty-state">
      <div class="empty-icon">🎟</div>
      <h3>Você ainda não tem ingressos</h3>
      <p>Explore os eventos disponíveis e faça sua compra.</p>
    </div>`;
    return;
  }

  const statusMap = {
    aprovado:  { label: 'Aprovado',  cls: 'badge-success' },
    pendente:  { label: 'Pendente',  cls: 'badge-warning' },
    cancelado: { label: 'Cancelado', cls: 'badge-error'   },
  };

  container.innerHTML = pedidos.map(p => `
    <div class="ticket-item">
      <div class="ticket-icon">${p.ingresso_emoji}</div>
      <div class="ticket-info">
        <div class="ticket-name">${p.ingresso_nome}</div>
        <div class="ticket-meta">
          ${fmt.date(p.data_pedido)} · ${fmt.method(p.tipo_pagamento)} · Qtd: ${p.quantidade}
        </div>
      </div>
      <div style="text-align:right">
        <div class="ticket-price">${fmt.currency(p.ingresso_preco * p.quantidade)}</div>
        <span class="badge ${statusMap[p.status].cls} mt-1">${statusMap[p.status].label}</span>
      </div>
    </div>
  `).join('');
}

function openCompraModal(id_ingresso) {
  const ing = dbRead.getIngressoById(id_ingresso);
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
  document.getElementById('compraTotal').textContent = fmt.currency(ing.preco);
  document.getElementById('compraPagamento').value = 'PIX';

  openModal('compraModal');
}

function updateCompraTotal() {
  const id  = parseInt(document.getElementById('compraIngressoId').value);
  const qtd = parseInt(document.getElementById('compraQtd').value) || 1;
  const ing = dbRead.getIngressoById(id);
  if (ing) document.getElementById('compraTotal').textContent = fmt.currency(ing.preco * qtd);
}

function handleCompra() {
  // Somente READ: apenas simula o envio para a fila SQS
  const ingNome = document.getElementById('compraIngressoNome').textContent;
  const pagamento = document.getElementById('compraPagamento').value;
  const qtd = document.getElementById('compraQtd').value;

  closeModal('compraModal');
  showToast(`Pedido enviado para processamento via SQS — ${ingNome} (${qtd}x, ${fmt.method(pagamento)})`, 'success');

  // Simula atualização visual (READ-ONLY: não altera DB)
  setTimeout(() => renderMeusPedidos(), 800);
}

/* ─── PAINEL DO ADMINISTRADOR ────────────────────── */
function loadAdminPanel() {
  const user = App.currentUser;
  document.getElementById('adminUserName').textContent = user.nome.split(' ')[0];

  loadAdminStats();
  loadAdminTab('ingressos');
}

function loadAdminStats() {
  const s = dbRead.getStats();
  document.getElementById('statUsuarios').textContent   = s.totalUsuarios;
  document.getElementById('statIngressos').textContent  = s.totalIngressos;
  document.getElementById('statPedidos').textContent    = s.pedidosAprovados;
  document.getElementById('statReceita').textContent    = fmt.currency(s.receita);
}

function loadAdminTab(tab) {
  document.querySelectorAll('#adminPanel .tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });

  const content = document.getElementById('adminTabContent');

  if (tab === 'ingressos') {
    const ingressos = dbRead.getAllIngressos();
    content.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">Ingressos</div>
          <div class="section-subtitle">Gerenciamento de eventos e ingressos</div>
        </div>
        <div class="flex gap-1">
          <button class="btn btn-secondary btn-sm" onclick="showToast('Operação de escrita desabilitada — somente leitura.', 'info')">
            + Novo Ingresso
          </button>
        </div>
      </div>
      <div class="alert alert-info">
        ℹ️ Modo somente leitura — operações de escrita são processadas pelos serviços de pagamento e processamento (SQS).
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Evento</th>
              <th>Data</th>
              <th>Preço</th>
              <th>Quantidade</th>
              <th>Status</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            ${ingressos.map(i => `
              <tr>
                <td class="mono text-muted">#${String(i.id_ingresso).padStart(3,'0')}</td>
                <td>
                  <div style="display:flex;align-items:center;gap:0.5rem">
                    <span>${i.emoji}</span>
                    <span style="font-weight:500">${i.nome}</span>
                  </div>
                </td>
                <td class="text-muted">${fmt.date(i.data)}</td>
                <td class="text-accent mono">${fmt.currency(i.preco)}</td>
                <td>
                  <span class="badge ${i.quantidade > 0 ? 'badge-success' : 'badge-error'}">
                    ${i.quantidade > 0 ? `${i.quantidade} disp.` : 'Esgotado'}
                  </span>
                </td>
                <td>
                  <span class="badge ${i.quantidade > 0 ? 'badge-info' : 'badge-muted'}">
                    ${i.quantidade > 0 ? 'Ativo' : 'Inativo'}
                  </span>
                </td>
                <td>
                  <div class="flex gap-1">
                    <button class="btn btn-ghost btn-sm" onclick="showToast('Edição indisponível — modo leitura.','info')">✏ Editar</button>
                    <button class="btn btn-danger btn-sm" onclick="showToast('Exclusão indisponível — modo leitura.','error')">✕</button>
                  </div>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  else if (tab === 'pedidos') {
    const pedidos = dbRead.getPedidosJoined();

    const statusMap = {
      aprovado:  { label: 'Aprovado',  cls: 'badge-success' },
      pendente:  { label: 'Pendente',  cls: 'badge-warning' },
      cancelado: { label: 'Cancelado', cls: 'badge-error'   },
    };

    content.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">Pedidos</div>
          <div class="section-subtitle">Histórico de compras processadas pelo sistema</div>
        </div>
        <div class="flex gap-1 items-center">
          <span class="badge badge-info">Via SQS</span>
          <span class="badge badge-muted">${pedidos.length} pedidos</span>
        </div>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID Pedido</th>
              <th>Usuário</th>
              <th>Ingresso</th>
              <th>Pagamento</th>
              <th>Qtd</th>
              <th>Total</th>
              <th>Data</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${pedidos.map(p => `
              <tr>
                <td class="mono text-muted">#${String(p.id_pedido).padStart(3,'0')}</td>
                <td>${p.usuario_nome}</td>
                <td>
                  <div style="display:flex;align-items:center;gap:0.4rem">
                    <span>${p.ingresso_emoji}</span>
                    <span>${p.ingresso_nome}</span>
                  </div>
                </td>
                <td><span class="badge badge-muted">${fmt.method(p.tipo_pagamento)}</span></td>
                <td class="mono">${p.quantidade}x</td>
                <td class="text-accent mono">${fmt.currency(p.ingresso_preco * p.quantidade)}</td>
                <td class="text-muted">${fmt.date(p.data_pedido)}</td>
                <td><span class="badge ${statusMap[p.status].cls}">${statusMap[p.status].label}</span></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  else if (tab === 'usuarios') {
    const usuarios = dbRead.getAllUsuarios();
    content.innerHTML = `
      <div class="section-header">
        <div>
          <div class="section-title">Usuários</div>
          <div class="section-subtitle">Todos os usuários cadastrados no sistema</div>
        </div>
        <div class="flex gap-1">
          <button class="btn btn-secondary btn-sm" onclick="showToast('Cadastro via interface de registro.','info')">
            + Novo Usuário
          </button>
        </div>
      </div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Nome</th>
              <th>E-mail</th>
              <th>Tipo</th>
              <th>Pedidos</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            ${usuarios.map(u => {
              const nPedidos = dbRead.getAllPedidos().filter(p => p.id_usuario === u.id_usuario).length;
              return `
                <tr>
                  <td class="mono text-muted">#${String(u.id_usuario).padStart(3,'0')}</td>
                  <td style="font-weight:500">${u.nome}</td>
                  <td class="text-muted">${u.email}</td>
                  <td>
                    <span class="badge ${u.tipo === 1 ? 'badge-warning' : 'badge-info'}">
                      ${u.tipo === 1 ? '⚙ Admin' : '👤 Usuário'}
                    </span>
                  </td>
                  <td class="mono">${nPedidos}</td>
                  <td>
                    <div class="flex gap-1">
                      <button class="btn btn-ghost btn-sm" onclick="showToast('Edição indisponível — modo leitura.','info')">✏ Editar</button>
                      <button class="btn btn-danger btn-sm" onclick="showToast('Exclusão indisponível — modo leitura.','error')">✕</button>
                    </div>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  else if (tab === 'dashboard') {
    const stats  = dbRead.getStats();
    const pedidos = dbRead.getPedidosJoined();

    const aprovados = pedidos.filter(p => p.status === 'aprovado').length;
    const cancelados = pedidos.filter(p => p.status === 'cancelado').length;
    const pendentes  = pedidos.filter(p => p.status === 'pendente').length;

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
          <div class="stat-value">${stats.totalPedidos}</div>
          <div class="stat-sub">Todos os status</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">Aprovados</div>
          <div class="stat-value">${aprovados}</div>
          <div class="stat-sub">Via SQS → Processamento</div>
        </div>
        <div class="stat-card danger">
          <div class="stat-label">Cancelados</div>
          <div class="stat-value">${cancelados}</div>
          <div class="stat-sub">Notificados via SNS</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">Pendentes</div>
          <div class="stat-value">${pendentes}</div>
          <div class="stat-sub">Na fila de pagamento</div>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 1.5rem">
        <div class="card">
          <div class="card-header">
            <span class="card-title">Fluxo AWS</span>
            <span class="badge badge-info">Arquitetura</span>
          </div>
          <div style="font-size:0.85rem; color: var(--text-muted); line-height: 2">
            <div>🌐 <strong style="color:var(--text)">Load Balancer</strong> → EC2 (Web)</div>
            <div>📦 <strong style="color:var(--text)">SQS</strong> → Serviço de Pagamento</div>
            <div>✅ <strong style="color:var(--text)">Aprovado</strong> → SQS → Processamento → RDS</div>
            <div>❌ <strong style="color:var(--text)">Recusado</strong> → SNS → E-mail cliente</div>
            <div>📊 <strong style="color:var(--text)">RDS</strong> → MySQL (tabelas abaixo)</div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">Tabelas do Banco</span>
            <span class="badge badge-muted">MySQL / RDS</span>
          </div>
          <div style="font-size:0.82rem; color: var(--text-muted); line-height:2">
            <div>👤 <strong style="color:var(--text)">usuarios</strong> — ${stats.totalUsuarios} registros</div>
            <div>🎟 <strong style="color:var(--text)">ingressos</strong> — ${stats.totalIngressos} registros</div>
            <div>🛒 <strong style="color:var(--text)">pedidos</strong>   — ${stats.totalPedidos} registros</div>
            <div style="margin-top:0.5rem; padding-top:0.5rem; border-top: 1px solid var(--border)">
              💰 Receita aprovada: <span class="text-accent mono">${fmt.currency(stats.receita)}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }
}

/* ─── TABS CLIENT ──────────────────────────────────── */
function loadClientTab(tab) {
  document.querySelectorAll('#clientPanel .tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });

  const sections = {
    ingressos: document.getElementById('clientIngressos'),
    meus:      document.getElementById('clientMeus'),
    conta:     document.getElementById('clientConta'),
  };

  Object.entries(sections).forEach(([key, el]) => {
    if (el) el.style.display = key === tab ? 'block' : 'none';
  });

  if (tab === 'conta') renderContaCliente();
}

function renderContaCliente() {
  const user = App.currentUser;
  const pedidos = dbRead.getPedidosByUsuario(user.id_usuario);
  const total = pedidos
    .filter(p => p.status === 'aprovado')
    .reduce((s, p) => s + p.ingresso_preco * p.quantidade, 0);

  document.getElementById('contaNome').textContent  = user.nome;
  document.getElementById('contaEmail').textContent = user.email;
  document.getElementById('contaTotalGasto').textContent = fmt.currency(total);
  document.getElementById('contaTotalPedidos').textContent = pedidos.length;
}

/* ─── INICIALIZAÇÃO ───────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  // Loader de tela
  setTimeout(() => {
    const loader = document.getElementById('loaderOverlay');
    if (loader) loader.classList.add('hidden');
    setTimeout(() => loader?.remove(), 500);
  }, 1400);

  // Exibir login
  showPage('login');

  // Form de login
  const loginForm = document.getElementById('loginForm');
  if (loginForm) loginForm.addEventListener('submit', handleLogin);

  // Fechar modal ao clicar fora
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.classList.remove('open');
    });
  });

  // Busca de ingressos (cliente)
  const searchInput = document.getElementById('clientSearch');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      renderIngressosDisponiveis(e.target.value);
    });
  }

  // Atualizar total na compra
  const compraQtd = document.getElementById('compraQtd');
  if (compraQtd) compraQtd.addEventListener('input', updateCompraTotal);

  const compraPag = document.getElementById('compraPagamento');
  if (compraPag) compraPag.addEventListener('change', updateCompraTotal);
});
