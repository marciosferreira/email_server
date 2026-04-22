// ---------------------------------------------------------
// Inbox / Sent
// ---------------------------------------------------------
async function showInbox() {
  setNav("inbox");
  showView("list");
  document.getElementById("list-title").textContent = "Caixa de Entrada";

  const res = await fetch(`${API}/emails/inbox`, { headers: authHeaders() });
  if (!res.ok) return;
  const data = await res.json();
  const messages = data.messages || [];
  renderEmailList(messages, "inbox");

  const unread = messages.filter(m => !m.read).length;
  const badge  = document.getElementById("badge-inbox");
  if (unread > 0) { badge.textContent = unread; badge.classList.remove("hidden"); }
  else            { badge.classList.add("hidden"); }
}

async function showSent() {
  setNav("sent");
  showView("list");
  document.getElementById("list-title").textContent = "Enviados";

  const res = await fetch(`${API}/emails/sent`, { headers: authHeaders() });
  if (!res.ok) return;
  const data = await res.json();
  renderEmailList(data.messages || [], "sent");
}

// ---------------------------------------------------------
// Render lista de emails
// ---------------------------------------------------------
function renderEmailList(messages, view) {
  const tbody = document.getElementById("email-list");
  if (!messages.length) {
    tbody.innerHTML = `<tr><td colspan="4" class="px-4 py-8 text-center text-gray-400">Nenhuma mensagem.</td></tr>`;
    return;
  }
  tbody.innerHTML = messages.map(m => {
    const isUnread = !m.read && view === "inbox";
    const weight   = isUnread ? "font-bold text-gray-900" : "text-gray-600";
    const dot      = isUnread
      ? `<span class="inline-block w-2 h-2 bg-blue-500 rounded-full mr-2 shrink-0"></span>` : "";

    let counterpart;
    if (view === "inbox") {
      counterpart = m.from;
    } else {
      const toStr = Array.isArray(m.to) ? m.to.join(", ") : m.to;
      const ccStr = Array.isArray(m.cc) && m.cc.length
        ? ` <span class="text-gray-400">(+CC)</span>` : "";
      counterpart = toStr + ccStr;
    }

    const ccBadge = (view === "inbox" && Array.isArray(m.cc) && m.cc.includes(state.email))
      ? `<span class="ml-1 text-xs bg-gray-100 text-gray-500 px-1 rounded">CC</span>` : "";

    return `
      <tr class="border-b cursor-pointer hover:bg-slate-50" onclick="readEmail('${m.id}')">
        <td class="px-4 py-3 text-sm ${weight} max-w-0 truncate">
          <div class="flex items-center">${dot}<span class="truncate">${counterpart}</span>${ccBadge}</div>
        </td>
        <td class="px-4 py-3 text-sm ${weight}">${m.subject}</td>
        <td class="px-4 py-3 text-xs text-gray-400 text-right whitespace-nowrap">${formatDateTime(m.timestamp)}</td>
        <td class="px-4 py-3 text-center">
          <button onclick="event.stopPropagation(); deleteEmail('${m.id}')"
            class="text-gray-300 hover:text-red-400 transition-colors text-base">🗑</button>
        </td>
      </tr>`;
  }).join("");
}

// ---------------------------------------------------------
// Leitura
// ---------------------------------------------------------
async function readEmail(id) {
  const res = await fetch(`${API}/emails/${id}`, { headers: authHeaders() });
  if (!res.ok) return;
  const msg = await res.json();
  state.currentEmailId = id;

  document.getElementById("read-subject").textContent = msg.subject;
  document.getElementById("read-from").textContent    = msg.from;
  document.getElementById("read-to").textContent      = Array.isArray(msg.to) ? msg.to.join(", ") : msg.to;
  document.getElementById("read-date").textContent    = formatDateTime(msg.timestamp);

  const ccRow = document.getElementById("read-cc-row");
  if (Array.isArray(msg.cc) && msg.cc.length) {
    document.getElementById("read-cc").textContent = msg.cc.join(", ");
    ccRow.classList.remove("hidden");
  } else {
    ccRow.classList.add("hidden");
  }

  document.getElementById("read-body").textContent = msg.body;
  showView("read");
}

async function backToList() {
  if (state.currentView === "sent") await showSent();
  else await showInbox();
}

// ---------------------------------------------------------
// Delete
// ---------------------------------------------------------
async function deleteEmail(id) {
  const res = await fetch(`${API}/emails/${id}`, { method: "DELETE", headers: authHeaders() });
  if (!res.ok) return;
  if (state.currentView === "sent") await showSent();
  else await showInbox();
}

async function deleteCurrentEmail() {
  if (!state.currentEmailId) return;
  await deleteEmail(state.currentEmailId);
  state.currentEmailId = null;
}

// ---------------------------------------------------------
// Composição
// ---------------------------------------------------------
function compose() {
  showView("compose");
  document.getElementById("compose-subject").value = "";
  document.getElementById("compose-body").value    = "";
  document.getElementById("compose-error").classList.add("hidden");
  document.getElementById("compose-ok").classList.add("hidden");
  Array.from(document.getElementById("compose-to").options).forEach(o => o.selected = false);
  Array.from(document.getElementById("compose-cc").options).forEach(o => o.selected = false);
}

async function sendEmail() {
  const toSel   = document.getElementById("compose-to");
  const ccSel   = document.getElementById("compose-cc");
  const subject = document.getElementById("compose-subject").value.trim();
  const body    = document.getElementById("compose-body").value.trim();
  const errEl   = document.getElementById("compose-error");
  const okEl    = document.getElementById("compose-ok");

  errEl.classList.add("hidden");
  okEl.classList.add("hidden");

  const toSelected = Array.from(toSel.selectedOptions).map(o => o.value);
  const ccSelected = Array.from(ccSel.selectedOptions).map(o => o.value);

  if (!toSelected.length) { errEl.textContent = "Selecione pelo menos um destinatário em 'Para'."; errEl.classList.remove("hidden"); return; }
  if (!subject)            { errEl.textContent = "Preencha o assunto.";                             errEl.classList.remove("hidden"); return; }
  if (!body)               { errEl.textContent = "Escreva a mensagem.";                             errEl.classList.remove("hidden"); return; }

  const res = await fetch(`${API}/emails/send`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ to: toSelected.join(","), cc: ccSelected.join(","), subject, body }),
  });

  if (!res.ok) {
    const data = await res.json();
    errEl.textContent = data.detail || "Erro ao enviar.";
    errEl.classList.remove("hidden");
    return;
  }

  okEl.classList.remove("hidden");
  setTimeout(() => showSent(), 1200);
}
