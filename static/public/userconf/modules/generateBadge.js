// static/public/userconf/modules/generateBadge.js

export default class GenerateBadge {
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
    if (!this.mount) throw new Error("GenerateBadge: mount no encontrado");
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
      <section class="uc-module generate-badge" aria-label="Generar gafete">
        <header class="uc-module__header">
          <h2 class="uc-module__title">Generar gafete</h2>
          <p class="uc-module__subtitle">Previsualiza y genera el gafete (pendiente de integrar API).</p>
        </header>

        <div class="uc-split">
          <div class="uc-card">
            <p class="uc-card__title">Usuario</p>
            <p class="uc-card__value">${hasUser ? this.escape(this.username) : "Ninguno"}</p>
            <p class="uc-card__hint">${
              hasUser ? "Puedes generar el gafete." : "Selecciona un usuario para continuar."
            }</p>

            <div class="uc-actions">
              <button type="button" class="uc-button" data-role="preview" ${
                hasUser ? "" : "disabled"
              }>Previsualizar</button>
              <button type="button" class="uc-button uc-button--primary" data-role="generate" ${
                hasUser ? "" : "disabled"
              }>Generar</button>
            </div>

            <p class="uc-status" data-role="status" aria-live="polite"></p>
          </div>

          <div class="uc-preview" aria-hidden="true">
            <div class="uc-preview__inner">
              <div class="uc-preview__photo"></div>
              <div class="uc-preview__meta">
                <div class="uc-preview__line uc-preview__line--strong">${
                  hasUser ? this.escape(this.username) : "usuario"
                }</div>
                <div class="uc-preview__line">Business System</div>
              </div>
            </div>
          </div>
        </div>
      </section>
    `;
  }

  render() {
    this.mount.innerHTML = this.template();
    this.previewBtn = this.mount.querySelector('[data-role="preview"]');
    this.generateBtn = this.mount.querySelector('[data-role="generate"]');
    this.statusEl = this.mount.querySelector('[data-role="status"]');
    this.setStatus("");
  }

  bindEvents() {
    if (this._bound) return;
    this._bound = true;

    this._onPreview = () => this.setStatus("Pendiente: previsualización real.");
    this._onGenerate = () => this.setStatus("Pendiente: generar gafete vía API.");

    this.previewBtn?.addEventListener("click", this._onPreview);
    this.generateBtn?.addEventListener("click", this._onGenerate);
  }

  unbindEvents() {
    if (!this._bound) return;
    this._bound = false;
    this.previewBtn?.removeEventListener("click", this._onPreview);
    this.generateBtn?.removeEventListener("click", this._onGenerate);
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

