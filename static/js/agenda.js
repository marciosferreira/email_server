// ---------------------------------------------------------
// Listar compromissos
// ---------------------------------------------------------
async function showAgenda() {
  setNav("agenda");
  showView("agenda");

  const dataIni = document.getElementById("agenda-filter-ini").value;
  const dataFim = document.getElementById("agenda-filter-fim").value;

  let url = `${API}/agenda`;
  if (dataIni && dataFim) url += `?data_ini=${dataIni}&data_fim=${dataFim}`;
  else if (dataIni)       url += `?data=${dataIni}`;

  const res = await fetch(url, { headers: authHeaders() });
  if (!res.ok) return;
  const data = await res.json();
  renderAgendaList(data.compromissos || []);
}

function renderAgendaList(items) {
  const container = document.getElementById("agenda-list");

  if (!items.length) {
    container.innerHTML = `<p class="text-center text-gray-400 py-10">Nenhum compromisso encontrado.</p>`;
    return;
  }

  // Agrupa por data
  const byDate = {};
  items.forEach(c => {
    if (!byDate[c.data]) byDate[c.data] = [];
    byDate[c.data].push(c);
  });

  container.innerHTML = Object.keys(byDate).sort().map(date => `
    <div class="mb-5">
      <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">${formatDate(date)}</h3>
      <div class="bg-white rounded-xl shadow-sm overflow-hidden divide-y divide-gray-100">
        ${byDate[date].map(c => `
          <div class="flex items-center gap-4 px-4 py-3 hover:bg-slate-50">
            <div class="text-sm font-mono text-blue-600 shrink-0 w-24">
              ${c.hora_inicio} – ${c.hora_fim}
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-semibold text-gray-800 truncate">${c.titulo}</p>
              ${c.descricao ? `<p class="text-xs text-gray-400 truncate">${c.descricao}</p>` : ""}
            </div>
            <div class="flex gap-2 shrink-0">
              <button onclick="openAgendaForm('${c.id}')"
                class="text-xs text-blue-500 hover:text-blue-700 border border-blue-200 hover:border-blue-400 px-2 py-1 rounded-lg transition-colors">
                Editar
              </button>
              <button onclick="deleteCompromisso('${c.id}')"
                class="text-xs text-red-400 hover:text-red-600 border border-red-200 hover:border-red-400 px-2 py-1 rounded-lg transition-colors">
                🗑
              </button>
            </div>
          </div>
        `).join("")}
      </div>
    </div>
  `).join("");
}

// ---------------------------------------------------------
// Filtros rápidos
// ---------------------------------------------------------
function filterAgendaHoje() {
  const hoje = new Date().toISOString().slice(0, 10);
  document.getElementById("agenda-filter-ini").value = hoje;
  document.getElementById("agenda-filter-fim").value = "";
  showAgenda();
}

function filterAgendaSemana() {
  const hoje   = new Date();
  const ini    = new Date(hoje);
  const fim    = new Date(hoje);
  ini.setDate(hoje.getDate() - hoje.getDay() + 1); // segunda-feira
  fim.setDate(ini.getDate() + 6);                  // domingo
  document.getElementById("agenda-filter-ini").value = ini.toISOString().slice(0, 10);
  document.getElementById("agenda-filter-fim").value = fim.toISOString().slice(0, 10);
  showAgenda();
}

function filterAgendaTodos() {
  document.getElementById("agenda-filter-ini").value = "";
  document.getElementById("agenda-filter-fim").value = "";
  showAgenda();
}

// ---------------------------------------------------------
// Formulário criar / editar
// ---------------------------------------------------------
async function openAgendaForm(id = null) {
  state.currentCompromissoId = id;
  clearAgendaForm();

  document.getElementById("agenda-form-title").textContent =
    id ? "Editar Compromisso" : "Novo Compromisso";

  if (id) {
    const res = await fetch(`${API}/agenda/${id}`, { headers: authHeaders() });
    if (!res.ok) return;
    const c = await res.json();
    document.getElementById("af-titulo").value      = c.titulo;
    document.getElementById("af-descricao").value   = c.descricao;
    document.getElementById("af-data").value        = c.data;
    document.getElementById("af-hora-ini").value    = c.hora_inicio;
    document.getElementById("af-hora-fim").value    = c.hora_fim;
  }

  showView("agenda-form");
}

function clearAgendaForm() {
  ["af-titulo","af-descricao","af-data","af-hora-ini","af-hora-fim"].forEach(id => {
    document.getElementById(id).value = "";
  });
  document.getElementById("af-error").classList.add("hidden");
}

async function saveCompromisso() {
  const titulo     = document.getElementById("af-titulo").value.trim();
  const descricao  = document.getElementById("af-descricao").value.trim();
  const data       = document.getElementById("af-data").value;
  const horaIni   = document.getElementById("af-hora-ini").value;
  const horaFim   = document.getElementById("af-hora-fim").value;
  const errEl      = document.getElementById("af-error");

  errEl.classList.add("hidden");

  if (!titulo)   { showFormError(errEl, "Preencha o título."); return; }
  if (!data)     { showFormError(errEl, "Informe a data."); return; }
  if (!horaIni)  { showFormError(errEl, "Informe o horário de início."); return; }
  if (!horaFim)  { showFormError(errEl, "Informe o horário de fim."); return; }

  const body = { titulo, descricao, data, hora_inicio: horaIni, hora_fim: horaFim };
  const id   = state.currentCompromissoId;
  const url  = id ? `${API}/agenda/${id}` : `${API}/agenda`;
  const method = id ? "PUT" : "POST";

  const res = await fetch(url, {
    method,
    headers: authHeaders(),
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json();
    const detail = err.detail;
    let msg;
    if (typeof detail === "object") {
      msg = detail.mensagem || detail.erro || JSON.stringify(detail);
    } else {
      msg = detail || "Erro ao salvar.";
    }
    showFormError(errEl, msg);
    return;
  }

  state.currentCompromissoId = null;
  await showAgenda();
}

function showFormError(el, msg) {
  el.textContent = msg;
  el.classList.remove("hidden");
}

async function deleteCompromisso(id) {
  const res = await fetch(`${API}/agenda/${id}`, { method: "DELETE", headers: authHeaders() });
  if (!res.ok) return;
  await showAgenda();
}
