import EditUser from "./modules/editUser.js";
import AddUser from "./modules/addUser.js";
import DeleteUser from "./modules/deleteUser.js";
import GenerateBadge from "./modules/generateBadge.js";
import UploadDocumentation from "./modules/uploadDocumentation.js";

const SEARCH_USERS_ENDPOINT = "/userconf/search_byusername";
const LOGIN_PATH = "/login/";

const state = {
  activeView: "edit",
  selectedUsername: null,
  selectedUserInfo: null,
  searchRequestId: 0,
  selectedUserRequestId: 0,
};

const MODULES = {
  edit: EditUser,
  add: AddUser,
  delete: DeleteUser,
  badge: GenerateBadge,
  docs: UploadDocumentation,
};

let activeModule = null;

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

function renderModuleState(message, kind = "info") {
  const mountEl = document.getElementById("module-root");
  if (!mountEl) return;
  mountEl.innerHTML = "";

  const el = document.createElement("div");
  el.className = `user-state${kind === "loading" ? " is-loading" : ""}${
    kind === "error" ? " is-error" : ""
  }`;
  el.textContent = message;
  mountEl.appendChild(el);
}

async function mountModule(view) {
  const mountEl = document.getElementById("module-root");
  if (!mountEl) return;

  try {
    if (activeModule?.destroy) activeModule.destroy();
  } finally {
    activeModule = null;
  }

  const ModuleClass = MODULES[view] || EditUser;
  activeModule = new ModuleClass({
    mount: mountEl,
    username: state.selectedUsername,
  });

  try {
    await activeModule.init();
    activeModule?.setUser?.(state.selectedUsername);
    if (state.selectedUserInfo) {
      activeModule?.setData?.(state.selectedUserInfo);
    }
  } catch (err) {
    const message = err?.message || "No se pudo cargar el módulo.";
    renderModuleState(message, "error");
  }
}

function setActiveTab(nextTab) {
  const tabs = document.querySelectorAll(".function-tabs .tab");
  tabs.forEach((tab) => tab.classList.toggle("is-active", tab === nextTab));
  state.activeView = nextTab?.dataset?.view || "edit";
  mountModule(state.activeView);
}

async function setSelectedUser(nextItem) {
  const items = document.querySelectorAll(".user-list .user-item");
  items.forEach((item) => {
    const selected = item === nextItem;
    item.classList.toggle("is-selected", selected);
    item.setAttribute("aria-selected", selected ? "true" : "false");
  });

  state.selectedUsername = nextItem?.dataset?.username || null;
  state.selectedUserInfo = null;
  const requestId = ++state.selectedUserRequestId;
  if (state.selectedUsername) {
    setHint(`Usuario seleccionado: ${state.selectedUsername}`, "info");
  }
  activeModule?.setUser?.(state.selectedUsername);

  if (!state.selectedUsername) return;

  activeModule?.setLoading?.(true);
  try {
    const data = await fetchUserInfo(state.selectedUsername);
    if (requestId !== state.selectedUserRequestId) return;
    if (!data) {
      setHint("No se encontró información del usuario.", "error");
      activeModule?.setStatus?.("No se encontró información del usuario.");
      return;
    }
    state.selectedUserInfo = data;
    activeModule?.setData?.(data);
  } catch (err) {
    if (requestId !== state.selectedUserRequestId) return;
    const message = err?.message || "No se pudo cargar la información.";
    setHint(message, "error");
    activeModule?.setStatus?.(message);
  } finally {
    if (requestId === state.selectedUserRequestId) {
      activeModule?.setLoading?.(false);
    }
  }
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
}

function removeUserFromList(username) {
  if (!username) return;
  const listEl = document.getElementById("user-list");
  if (!listEl) return;

  let removed = false;
  document.querySelectorAll(".user-list .user-item").forEach((item) => {
    if (item.dataset.username === username) {
      item.remove();
      removed = true;
    }
  });

  if (removed && listEl.children.length === 0) {
    renderUserListState("Sin resultados.", "info");
  }
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

async function fetchUserInfo(username) {
  const baseUrl = window.location.origin;
  const auth = getAuthHeader();
  if (!auth) {
    throw new Error("Necesitas iniciar sesión para ver la información.");
  }

  const url = new URL(
    `${baseUrl}/userconf/get_userinfo/${encodeURIComponent(username)}`
  );

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: { Authorization: auth },
  });

  if (res.status === 401) {
    setHint("Sesión expirada. Redirigiendo a login…", "error");
    setTimeout(() => {
      window.location.href = new URL(LOGIN_PATH, baseUrl).toString();
    }, 400);
    return null;
  }

  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const msg = data?.detail || "No se pudo cargar la información del usuario.";
    throw new Error(msg);
  }

  return data;
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
    activeModule?.setUser?.(state.selectedUsername);
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

  const input = document.getElementById("user-search");
  const searchBtn = document.getElementById("user-search-btn");
  const debounced = debounce(runSearch, 250);

  input?.addEventListener("input", debounced);
  input?.addEventListener("search", runSearch);
  input?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") runSearch();
  });
  searchBtn?.addEventListener("click", runSearch);

  window.addEventListener("userconf:deleted", (event) => {
    const deletedUsername = event?.detail?.username;
    if (!deletedUsername) return;
    removeUserFromList(deletedUsername);
    if (state.selectedUsername === deletedUsername) {
      state.selectedUsername = null;
      state.selectedUserInfo = null;
      setHint("Usuario eliminado.", "info");
      activeModule?.setUser?.(null);
    }
  });
});
