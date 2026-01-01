// static/public/userconf/modules/addUser.js

export default class AddUser {
  /**
   * @param {Object} options
   * @param {HTMLElement|string} options.mount Punto de montaje (elemento o selector)
   * @param {string} [options.apiBase] Base URL para endpoints (si aplica)
   */
  constructor({ mount, apiBase = "/userconf" } = {}) {
    this.apiBase = apiBase;
    this.mount = typeof mount === "string" ? document.querySelector(mount) : mount;
    this._bound = false;
  }

  async init() {
    if (!this.mount) throw new Error("AddUser: mount no encontrado");
    this.render();
    this.bindEvents();
  }

  destroy() {
    this.unbindEvents();
    this.mount.innerHTML = "";
  }

  template() {
    return `
      <section class="uc-module add-user" aria-label="Agregar usuario">
        <header class="uc-module__header">
          <h2 class="uc-module__title">Agregar usuario</h2>
          <p class="uc-module__subtitle">Crea un usuario nuevo (pendiente de integrar API).</p>
        </header>

        <form class="uc-form" data-role="form">
          <div class="uc-field">
            <label for="au-username">Usuario</label>
            <input id="au-username" name="username" type="text" autocomplete="username" placeholder="usuario" />
          </div>

          <div class="uc-field">
            <label for="au-fullname">Nombre completo</label>
            <input id="au-fullname" name="fullname" type="text" autocomplete="name" placeholder="Nombre Apellido" />
          </div>

          <div class="uc-field">
            <label for="au-type">Tipo</label>
            <select id="au-type" name="typeUser">
              <option value="3">manager</option>
              <option value="2">admin</option>
              <option value="1">superadmin</option>
              <option value="4">vendor</option>
              <option value="5">customer</option>
            </select>
          </div>

          <div class="uc-actions">
            <button type="button" class="uc-button" data-role="reset">Limpiar</button>
            <button type="submit" class="uc-button uc-button--primary" data-role="submit">Crear</button>
          </div>

          <p class="uc-status" data-role="status" aria-live="polite"></p>
        </form>
      </section>
    `;
  }

  render() {
    this.mount.innerHTML = this.template();
    this.form = this.mount.querySelector('[data-role="form"]');
    this.statusEl = this.mount.querySelector('[data-role="status"]');
    this.resetBtn = this.mount.querySelector('[data-role="reset"]');
    this.setStatus("");
  }

  bindEvents() {
    if (this._bound) return;
    this._bound = true;

    this._onSubmit = (e) => {
      e.preventDefault();
      this.setStatus("Pendiente: implementar creación vía API.");
    };

    this._onReset = () => {
      this.form?.reset();
      this.setStatus("");
    };

    this.form?.addEventListener("submit", this._onSubmit);
    this.resetBtn?.addEventListener("click", this._onReset);
  }

  unbindEvents() {
    if (!this._bound) return;
    this._bound = false;
    this.form?.removeEventListener("submit", this._onSubmit);
    this.resetBtn?.removeEventListener("click", this._onReset);
  }

  setStatus(message) {
    if (this.statusEl) this.statusEl.textContent = message || "";
  }
}

