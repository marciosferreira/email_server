const API = "";

let state = {
  token: null,
  email: null,
  name: null,
  currentView: "inbox",       // inbox | sent | read | compose | agenda | agenda-form
  currentFolder: "inbox",     // inbox | sent
  currentEmailId: null,
  currentCompromissoId: null, // null = criar, string = editar
};

let allUsers = [];

function authHeaders() {
  return {
    "Authorization": `Bearer ${state.token}`,
    "Content-Type": "application/json",
  };
}

function formatDateTime(iso) {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
}

function formatDate(ymd) {
  const [y, m, d] = ymd.split("-");
  return `${d}/${m}/${y}`;
}

const ALL_VIEWS = ["list", "read", "compose", "agenda", "agenda-form"];

function showView(name) {
  state.currentView = name;
  ALL_VIEWS.forEach(v =>
    document.getElementById(`view-${v}`).classList.toggle("hidden", v !== name)
  );
}

const NAV_BASE = "flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm font-medium ";
const NAV_ACTIVE = "text-blue-700 bg-blue-50";
const NAV_IDLE   = "text-gray-600 hover:bg-gray-100";

function setNav(active) {
  ["inbox", "sent", "agenda"].forEach(key => {
    const el = document.getElementById(`nav-${key}`);
    if (el) el.className = NAV_BASE + (active === key ? NAV_ACTIVE : NAV_IDLE);
  });
}
