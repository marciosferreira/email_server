async function doLogin() {
  const token    = document.getElementById("login-token").value.trim();
  const password = document.getElementById("login-password").value.trim();
  const errEl    = document.getElementById("login-error");
  errEl.classList.add("hidden");

  try {
    const res = await fetch(`${API}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, password }),
    });
    if (!res.ok) {
      const data = await res.json();
      const detail = data.detail;
      errEl.textContent = typeof detail === "object" ? detail.erro : detail || "Credenciais inválidas.";
      errEl.classList.remove("hidden");
      return;
    }
    const user = await res.json();
    applySession(user);
    localStorage.setItem("session", JSON.stringify({ token: user.token, email: user.email, name: user.name }));
    await postLogin();
  } catch {
    errEl.textContent = "Erro de conexão com o servidor.";
    errEl.classList.remove("hidden");
  }
}

function applySession(user) {
  state.token = user.token;
  state.email = user.email;
  state.name  = user.name;
  document.getElementById("header-email").textContent = user.email;
  document.getElementById("screen-login").classList.add("hidden");
  document.getElementById("screen-app").classList.remove("hidden");
}

async function postLogin() {
  await loadUsers();
  await showInbox();
}

function doLogout() {
  state.token = null;
  state.email = null;
  state.name  = null;
  state.currentEmailId = null;
  state.currentCompromissoId = null;
  localStorage.removeItem("session");
  document.getElementById("screen-app").classList.add("hidden");
  document.getElementById("screen-login").classList.remove("hidden");
  document.getElementById("login-token").value    = "";
  document.getElementById("login-password").value = "";
}

document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("login-password").addEventListener("keydown", e => {
    if (e.key === "Enter") doLogin();
  });

  const saved = localStorage.getItem("session");
  if (saved) {
    try {
      applySession(JSON.parse(saved));
      await postLogin();
    } catch {
      localStorage.removeItem("session");
    }
  }
});

async function loadUsers() {
  const res = await fetch(`${API}/users`, { headers: authHeaders() });
  if (!res.ok) return;
  allUsers = await res.json();
  populateSelects();
}

function populateSelects() {
  const others = allUsers.filter(u => u.email !== state.email);
  const opts   = others.map(u =>
    `<option value="${u.email}">${u.name} &lt;${u.email}&gt;</option>`
  ).join("");
  document.getElementById("compose-to").innerHTML = opts;
  document.getElementById("compose-cc").innerHTML = opts;
}
