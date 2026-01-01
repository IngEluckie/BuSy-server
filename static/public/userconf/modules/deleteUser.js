// static/public/userconf/modules/deleteUser.js

export default class DeleteUser {
  /**
   * @param {Object} options
   * @param {HTMLElement|string} options.mount Punto de montaje (elemento o selector)
   * @param {string} [options.username] Usuario objetivo (si aplica)
   * @param {string} [options.apiBase] Base URL para endpoints (si aplica)
   */
  constructor({ mount, username = null, apiBase = "/userconf" } = {}) {
    this.apiBase = apiBase;
    this.username = username;
    this.mount = typeof mount === "string" ? document.querySelector(mount) : mount;
    this._bound = false;
  }

  async init() {
    if (!this.mount) throw new Error("DeleteUser: mount no encontrado");
    this.render();
    this.bindEvents();
  }

  destroy() {
    this.unbindEvents();
    this.mount.innerHTML = "";
  }

  setUser(username) {
    this.username = username || null;
    this.render();
  }

  template() {
    const hasUser = Boolean(this.username);
    return `
      <section class="uc-module delete-user" aria-label="Eliminar usuario">
        <header class="uc-module__header">
          <h2 class="uc-module__title">Eliminar usuario</h2>
          <p class="uc-module__subtitle">Acción irreversible (pendiente de integrar API).</p>
        </header>

        <div class="uc-card uc-card--danger">
          <p class="uc-card__title">Usuario seleccionado</p>
          <p class="uc-card__value">${hasUser ? this.escape(this.username) : "Ninguno"}</p>
          <p class="uc-card__hint">${
            hasUser
              ? "Confirma para eliminar."
              : "Selecciona un usuario en el panel izquierdo."
          }</p>

          <div class="uc-actions">
            <button type="button" class="uc-button" data-role="cancel">Cancelar</button>
            <button type="button" class="uc-button uc-button--danger" data-role="confirm" ${
              hasUser ? "" : "disabled"
            }>Eliminar</button>
          </div>

          <p class="uc-status" data-role="status" aria-live="polite"></p>
        </div>
      </section>
    `;
  }

  render() {
    this.mount.innerHTML = this.template();
    this.cancelBtn = this.mount.querySelector('[data-role="cancel"]');
    this.confirmBtn = this.mount.querySelector('[data-role="confirm"]');
    this.statusEl = this.mount.querySelector('[data-role="status"]');
    this.setStatus("");
  }

  bindEvents() {
    if (this._bound) return;
    this._bound = true;

    this._onCancel = () => this.setStatus("");
    this._onConfirm = () => {
      if (!this.username) return;
      this.setStatus("Pendiente: implementar eliminación vía API.");
    };

    this.cancelBtn?.addEventListener("click", this._onCancel);
    this.confirmBtn?.addEventListener("click", this._onConfirm);
  }

  unbindEvents() {
    if (!this._bound) return;
    this._bound = false;
    this.cancelBtn?.removeEventListener("click", this._onCancel);
    this.confirmBtn?.removeEventListener("click", this._onConfirm);
  }

  setStatus(message) {
    if (this.statusEl) this.statusEl.textContent = message || "";
  }

  escape(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }
}

