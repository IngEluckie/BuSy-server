const API_USERS_ENDPOINT = "/api/users";
const SEARCH_USERS_ENDPOINT = "/userconf/search_byusername";
const LOGIN_PATH = "/login/";

const state = {
  activeView: "edit",
  selectedUsername: null,
  selectedUserInfo: null,
  searchRequestId: 0,
};

function getAuthHeader() {
  const token = localStorage.getItem("busy_token");
  const tokenType = localStorage.getItem("busy_token_type") || "bearer";
  if (!token) return null;
  return `${tokenType} ${token}`;
}

function setHint(message, kind = "info") {
  const hintEl = document.getElementById("user-hint");
  if (!hintEl) return;
  hintEl.textContent = message;
  hintEl.dataset.kind = kind;
}

function renderUserListState(message, kind = "info") {
  const listEl = document.getElementById("user-list");
  if (!listEl) return;
  listEl.innerHTML = "";
  const el = document.createElement("div");
  el.className = `user-state${kind === "loading" ? " is-loading" : ""}${
    kind === "error" ? " is-error" : ""
  }`;
  el.textContent = message;
  listEl.appendChild(el);
}

function updatePlaceholder() {
  const content = document.getElementById("function-content");
  const titleEl = content?.querySelector(".placeholder-title");
  const textEl = content?.querySelector(".placeholder-text");

  const activeTab = document.querySelector(".function-tabs .tab.is-active");
  const title = activeTab?.textContent?.trim() || "Editar usuario";
  if (titleEl) titleEl.textContent = title;

  const userLabel =
    state.selectedUserInfo?.fullname ||
    state.selectedUsername ||
    "un usuario";

  const copy = {
    edit: `Modifica los datos de ${userLabel}.`,
    add: "Crea un usuario nuevo (pendiente de definir campos).",
    delete: `Elimina a ${userLabel} (requiere confirmación).`,
    badge: `Genera un gafete para ${userLabel}.`,
    docs: `Consulta o genera documentación de ${userLabel}.`,
  };

  if (textEl) {
    textEl.textContent =
      copy[state.activeView] ||
      "Selecciona un usuario y una función para ver el módulo aquí.";
  }
}

function setActiveTab(nextTab) {
  const tabs = document.querySelectorAll(".function-tabs .tab");
  tabs.forEach((tab) => tab.classList.toggle("is-active", tab === nextTab));
  state.activeView = nextTab?.dataset?.view || "edit";
  updatePlaceholder();
}

function setSelectedUser(nextItem) {
  const items = document.querySelectorAll(".user-list .user-item");
  items.forEach((item) => {
    const selected = item === nextItem;
    item.classList.toggle("is-selected", selected);
    item.setAttribute("aria-selected", selected ? "true" : "false");
  });

  state.selectedUsername = nextItem?.dataset?.username || null;
  state.selectedUserInfo = null;
  if (state.selectedUsername) setHint(`Usuario seleccionado: ${state.selectedUsername}`, "info");
  updatePlaceholder();
}

function createUserItem(username) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "user-item";
  btn.setAttribute("role", "option");
  btn.setAttribute("aria-selected", "false");
  btn.dataset.username = username;

  const avatar = document.createElement("span");
  avatar.className = "user-avatar";
  avatar.setAttribute("aria-hidden", "true");

  const meta = document.createElement("span");
  meta.className = "user-meta";

  const name = document.createElement("span");
  name.className = "user-name";
  name.textContent = username;

  const sub = document.createElement("span");
  sub.className = "user-sub";
  sub.textContent = "Pulsa para seleccionar";

  meta.appendChild(name);
  meta.appendChild(sub);
  btn.appendChild(avatar);
  btn.appendChild(meta);

  btn.addEventListener("click", () => setSelectedUser(btn));
  return btn;
}

function renderUserList(usernames) {
  const listEl = document.getElementById("user-list");
  if (!listEl) return;
  listEl.innerHTML = "";
  state.selectedUsername = null;
  state.selectedUserInfo = null;

  if (!Array.isArray(usernames) || usernames.length === 0) {
    renderUserListState("Sin resultados.", "info");
    return;
  }

  usernames.forEach((username) => {
    const item = createUserItem(String(username));
    listEl.appendChild(item);
  });

  updatePlaceholder();
}

async function searchUsers(username, limit = 10) {
  const baseUrl = window.location.origin;
  const auth = getAuthHeader();
  if (!auth) {
    throw new Error("Necesitas iniciar sesión para buscar usuarios.");
  }

  const url = new URL(
    `${baseUrl}${SEARCH_USERS_ENDPOINT}/${encodeURIComponent(username)}`
  );
  url.searchParams.set("limit", String(limit));

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: { Authorization: auth },
  });

  if (res.status === 401) {
    setHint("Sesión expirada. Redirigiendo a login…", "error");
    setTimeout(() => {
      window.location.href = new URL(LOGIN_PATH, baseUrl).toString();
    }, 400);
    return [];
  }

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const msg = data?.detail || "No se pudo buscar usuarios.";
    throw new Error(msg);
  }

  return Array.isArray(data) ? data : [];
}

function debounce(fn, delayMs) {
  let t = null;
  return (...args) => {
    if (t) window.clearTimeout(t);
    t = window.setTimeout(() => fn(...args), delayMs);
  };
}

async function runSearch() {
  const input = document.getElementById("user-search");
  const query = (input?.value || "").trim();
  const requestId = ++state.searchRequestId;

  if (!query) {
    state.selectedUsername = null;
    state.selectedUserInfo = null;
    setHint("Escribe para buscar usuarios (vía API).", "info");
    renderUserListState("Escribe para buscar.", "info");
    updatePlaceholder();
    return;
  }

  setHint("Buscando…", "info");
  renderUserListState("Buscando…", "loading");

  try {
    const usernames = await searchUsers(query);
    if (requestId !== state.searchRequestId) return;
    renderUserList(usernames);
    setHint(
      usernames.length ? `Resultados: ${usernames.length}` : "Sin resultados.",
      "info",
    );
  } catch (err) {
    if (requestId !== state.searchRequestId) return;
    const message = err?.message || "Error al buscar usuarios.";
    setHint(message, "error");
    renderUserListState(message, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  renderUserListState("Escribe para buscar.", "info");

  document.querySelectorAll(".function-tabs .tab").forEach((tab) => {
    tab.addEventListener("click", () => setActiveTab(tab));
  });

  const defaultTab = document.querySelector(".function-tabs .tab.is-active");
  if (defaultTab) setActiveTab(defaultTab);
  updatePlaceholder();

  const input = document.getElementById("user-search");
  const searchBtn = document.getElementById("user-search-btn");
  const debounced = debounce(runSearch, 250);

  input?.addEventListener("input", debounced);
  input?.addEventListener("search", runSearch);
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runSearch();
  });
  searchBtn?.addEventListener("click", runSearch);
});
