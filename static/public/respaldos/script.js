const LOGIN_PATH = "/login/";
const ADMIN_TYPES = new Set([1, 2]);

const els = {
  backButton: document.getElementById("back-button"),
  downloadButton: document.getElementById("download-button"),
  uploadForm: document.getElementById("upload-form"),
  fileInput: document.getElementById("busy-file"),
  fileName: document.getElementById("file-name"),
  status: document.getElementById("status"),
  refreshBackupsButton: document.getElementById("refresh-backups-button"),
  automaticBackupsList: document.getElementById("automatic-backups-list"),
  confirmModal: document.getElementById("confirm-modal"),
  cancelUploadButton: document.getElementById("cancel-upload-button"),
  acceptUploadButton: document.getElementById("accept-upload-button"),
};

let pendingUploadFile = null;
let lastFocusedElement = null;

function getAuthHeader() {
  const token = localStorage.getItem("busy_token");
  const tokenType = localStorage.getItem("busy_token_type") || "bearer";
  if (!token) return null;
  return `${tokenType} ${token}`;
}

function setStatus(message, kind = "info") {
  if (!els.status) return;
  els.status.textContent = message;
  els.status.dataset.kind = kind;
}

function setBusy(isBusy) {
  if (els.downloadButton) els.downloadButton.disabled = isBusy;
  if (els.refreshBackupsButton) els.refreshBackupsButton.disabled = isBusy;
  els.uploadForm?.querySelectorAll("button, input").forEach((el) => {
    el.disabled = isBusy;
  });
  els.automaticBackupsList?.querySelectorAll("button").forEach((el) => {
    el.disabled = isBusy;
  });
}

async function apiFetch(url, options = {}) {
  const auth = getAuthHeader();
  if (!auth) {
    window.location.href = LOGIN_PATH;
    throw new Error("Sesión requerida.");
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      Authorization: auth,
      ...(options.headers || {}),
    },
  });

  if (response.status === 401) {
    window.location.href = LOGIN_PATH;
    throw new Error("Sesión expirada.");
  }

  if (!response.ok) {
    let detail = "No se pudo completar la operación.";
    try {
      const body = await response.json();
      detail = body?.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response;
}

function filenameFromDisposition(disposition) {
  if (!disposition) return ".busy";
  const utfMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch?.[1]) {
    return decodeURIComponent(utfMatch[1]);
  }
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return match?.[1] || ".busy";
}

function isBusyUploadFilename(filename) {
  const normalized = String(filename || "").toLowerCase();
  return normalized === "busy" || normalized.endsWith(".busy");
}

function formatBytes(bytes) {
  const value = Number(bytes) || 0;
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function renderBackupListState(message, kind = "info") {
  if (!els.automaticBackupsList) return;
  els.automaticBackupsList.innerHTML = "";
  const el = document.createElement("div");
  el.className = `empty-state${kind === "error" ? " is-error" : ""}`;
  el.textContent = message;
  els.automaticBackupsList.appendChild(el);
}

function downloadBlob(response) {
  return response.blob().then((blob) => {
    const filename = filenameFromDisposition(response.headers.get("content-disposition"));
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    return filename;
  });
}

async function ensureAdmin() {
  const response = await apiFetch("/auth/me");
  const user = await response.json();
  if (!ADMIN_TYPES.has(Number(user?.typeUser))) {
    throw new Error("No tienes permisos para administrar respaldos.");
  }
}

async function downloadBackup() {
  setBusy(true);
  setStatus("Preparando descarga...");

  try {
    const response = await apiFetch("/respaldos/download");
    await downloadBlob(response);
    setStatus("Respaldo descargado.", "success");
  } catch (err) {
    setStatus(err?.message || "No se pudo descargar el respaldo.", "error");
  } finally {
    setBusy(false);
  }
}

async function downloadAutomaticBackup(filename) {
  setBusy(true);
  setStatus("Preparando descarga...");

  try {
    const response = await apiFetch(
      `/respaldos/automatic-backups/${encodeURIComponent(filename)}`
    );
    await downloadBlob(response);
    setStatus("Respaldo automático descargado.", "success");
  } catch (err) {
    setStatus(err?.message || "No se pudo descargar el respaldo automático.", "error");
  } finally {
    setBusy(false);
  }
}

function renderAutomaticBackups(backups) {
  if (!els.automaticBackupsList) return;
  els.automaticBackupsList.innerHTML = "";

  if (!Array.isArray(backups) || backups.length === 0) {
    renderBackupListState("Aún no hay respaldos automáticos.");
    return;
  }

  backups.forEach((backup) => {
    const item = document.createElement("article");
    item.className = "backup-item";

    const meta = document.createElement("div");
    meta.className = "backup-item-meta";

    const name = document.createElement("strong");
    name.textContent = backup.filename || "Respaldo automático";

    const detail = document.createElement("span");
    const dateText = formatDate(backup.modifiedAt);
    const sizeText = formatBytes(backup.size);
    detail.textContent = [dateText, sizeText].filter(Boolean).join(" · ");

    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary-button compact-button";
    button.textContent = "Descargar";
    button.addEventListener("click", () => downloadAutomaticBackup(backup.filename));

    meta.appendChild(name);
    meta.appendChild(detail);
    item.appendChild(meta);
    item.appendChild(button);
    els.automaticBackupsList.appendChild(item);
  });
}

async function loadAutomaticBackups() {
  renderBackupListState("Cargando respaldos automáticos...");

  try {
    const response = await apiFetch("/respaldos/automatic-backups");
    const data = await response.json();
    renderAutomaticBackups(data?.backups || []);
  } catch (err) {
    renderBackupListState(
      err?.message || "No se pudieron cargar los respaldos automáticos.",
      "error"
    );
  }
}

function openConfirmModal(file) {
  if (!els.confirmModal || !els.acceptUploadButton) {
    performUpload(file);
    return;
  }
  pendingUploadFile = file;
  lastFocusedElement = document.activeElement;
  els.confirmModal.hidden = false;
  els.acceptUploadButton.focus();
}

function closeConfirmModal() {
  if (!els.confirmModal) return;
  els.confirmModal.hidden = true;
  pendingUploadFile = null;
  lastFocusedElement?.focus?.();
  lastFocusedElement = null;
}

async function performUpload(file) {
  const formData = new FormData();
  formData.append("file", file);

  setBusy(true);
  setStatus("Subiendo y validando respaldo...");

  try {
    const response = await apiFetch("/respaldos/upload", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    const backupText = data?.backup ? ` Respaldo automático: ${data.backup}.` : "";
    setStatus(`Archivo .busy reemplazado.${backupText}`, "success");
    els.uploadForm?.reset();
    if (els.fileName) els.fileName.textContent = "Seleccionar archivo .busy";
    await loadAutomaticBackups();
  } catch (err) {
    setStatus(err?.message || "No se pudo subir el respaldo.", "error");
  } finally {
    setBusy(false);
  }
}

async function uploadBackup(event) {
  event.preventDefault();

  const file = els.fileInput?.files?.[0];
  if (!file) {
    setStatus("Selecciona un archivo .busy.", "error");
    return;
  }

  if (!isBusyUploadFilename(file.name)) {
    setStatus("El archivo debe ser un respaldo .busy.", "error");
    return;
  }

  openConfirmModal(file);
}

function bindEvents() {
  els.backButton?.addEventListener("click", () => {
    window.location.href = "/";
  });
  els.downloadButton?.addEventListener("click", downloadBackup);
  els.refreshBackupsButton?.addEventListener("click", loadAutomaticBackups);
  els.uploadForm?.addEventListener("submit", uploadBackup);
  els.fileInput?.addEventListener("change", () => {
    const file = els.fileInput.files?.[0];
    if (els.fileName) {
      els.fileName.textContent = file?.name || "Seleccionar archivo .busy";
    }
  });
  els.cancelUploadButton?.addEventListener("click", closeConfirmModal);
  els.acceptUploadButton?.addEventListener("click", async () => {
    const file = pendingUploadFile;
    closeConfirmModal();
    if (file) await performUpload(file);
  });
  els.confirmModal?.addEventListener("click", (event) => {
    if (event.target === els.confirmModal) closeConfirmModal();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !els.confirmModal?.hidden) {
      closeConfirmModal();
    }
  });
}

async function init() {
  bindEvents();
  setBusy(true);
  setStatus("Verificando sesión...");

  try {
    await ensureAdmin();
    await loadAutomaticBackups();
    setStatus("Listo.");
  } catch (err) {
    setStatus(err?.message || "No se pudo verificar la sesión.", "error");
    if (els.downloadButton) els.downloadButton.disabled = true;
    if (els.refreshBackupsButton) els.refreshBackupsButton.disabled = true;
    els.uploadForm?.querySelectorAll("button, input").forEach((el) => {
      el.disabled = true;
    });
    return;
  }

  setBusy(false);
}

init();
