// static/public/userconf/modules/uploadDocumentation.js

export default class UploadDocumentation {
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
    if (!this.mount) throw new Error("UploadDocumentation: mount no encontrado");
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
      <section class="uc-module upload-docs" aria-label="Documentación">
        <header class="uc-module__header">
          <h2 class="uc-module__title">Documentación</h2>
          <p class="uc-module__subtitle">Sube archivos del usuario (pendiente de integrar API).</p>
        </header>

        <div class="uc-card">
          <p class="uc-card__title">Usuario</p>
          <p class="uc-card__value">${hasUser ? this.escape(this.username) : "Ninguno"}</p>
          <p class="uc-card__hint">${
            hasUser
              ? "Selecciona archivos y súbelos."
              : "Selecciona un usuario en el panel izquierdo."
          }</p>

          <div class="uc-field">
            <label for="ud-files">Archivos</label>
            <input id="ud-files" type="file" ${hasUser ? "" : "disabled"} multiple />
          </div>

          <div class="uc-actions">
            <button type="button" class="uc-button" data-role="clear" ${
              hasUser ? "" : "disabled"
            }>Limpiar</button>
            <button type="button" class="uc-button uc-button--primary" data-role="upload" ${
              hasUser ? "" : "disabled"
            }>Subir</button>
          </div>

          <p class="uc-status" data-role="status" aria-live="polite"></p>
        </div>
      </section>
    `;
  }

  render() {
    this.mount.innerHTML = this.template();
    this.filesEl = this.mount.querySelector("#ud-files");
    this.clearBtn = this.mount.querySelector('[data-role="clear"]');
    this.uploadBtn = this.mount.querySelector('[data-role="upload"]');
    this.statusEl = this.mount.querySelector('[data-role="status"]');
    this.setStatus("");
  }

  bindEvents() {
    if (this._bound) return;
    this._bound = true;

    this._onClear = () => {
      if (this.filesEl) this.filesEl.value = "";
      this.setStatus("");
    };
    this._onUpload = () => this.setStatus("Pendiente: subir documentación vía API.");

    this.clearBtn?.addEventListener("click", this._onClear);
    this.uploadBtn?.addEventListener("click", this._onUpload);
  }

  unbindEvents() {
    if (!this._bound) return;
    this._bound = false;
    this.clearBtn?.removeEventListener("click", this._onClear);
    this.uploadBtn?.removeEventListener("click", this._onUpload);
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

