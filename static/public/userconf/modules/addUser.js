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
          <p class="uc-module__subtitle">Crea un usuario nuevo.</p>
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
            <label for="au-birthday">Cumpleanos</label>
            <input id="au-birthday" name="birthday" type="date" autocomplete="bday" />
          </div>

          <div class="uc-field">
            <label for="au-rfc">RFC</label>
            <input id="au-rfc" name="rfc" type="text" autocomplete="off" />
          </div>

          <div class="uc-field">
            <label for="au-cellphone">Celular</label>
            <input id="au-cellphone" name="cellphone" type="tel" autocomplete="tel" />
          </div>

          <div class="uc-field">
            <label for="au-email">Email</label>
            <input id="au-email" name="email" type="email" autocomplete="email" />
          </div>

          <div class="uc-field">
            <label for="au-type">Tipo</label>
            <select id="au-type" name="typeUser">
              <option value="">Selecciona un tipo</option>
              <option value="1">superadmin</option>
              <option value="2">admin</option>
              <option value="3">manager</option>
              <option value="4">vendor</option>
              <option value="5">customer</option>
            </select>
          </div>

          <div class="uc-field">
            <label for="au-password">Contrasena</label>
            <input id="au-password" name="pw" type="password" autocomplete="new-password" placeholder="******" />
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
      this.handleSubmit();
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

  async handleSubmit() {
    const payload = this.readForm();
    const validationError = this.validate(payload);
    if (validationError) {
      this.setStatus(validationError);
      return;
    }

    try {
      const auth = this.getAuthHeader();
      if (!auth) {
        throw new Error("Necesitas iniciar sesión para crear usuarios.");
      }

      const baseUrl = window.location.origin;
      const encodedUserinfo = encodeURIComponent(JSON.stringify(payload));
      const url = `${baseUrl}${this.apiBase}/create_user:${encodedUserinfo}`;

      const res = await fetch(url, {
        method: "POST",
        headers: { Authorization: auth },
      });

      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const msg = data?.detail || "No se pudo crear el usuario.";
        throw new Error(msg);
      }

      this.form?.reset();
      this.setStatus(data?.message || "Usuario creado.");
    } catch (err) {
      this.setStatus(err?.message || "No se pudo crear el usuario.");
    }
  }

  readForm() {
    const formData = new FormData(this.form);
    return {
      username: (formData.get("username") || "").trim(),
      fullname: (formData.get("fullname") || "").trim(),
      birthday: formData.get("birthday") || "",
      rfc: (formData.get("rfc") || "").trim(),
      cellphone: (formData.get("cellphone") || "").trim(),
      email: (formData.get("email") || "").trim(),
      typeUser: (formData.get("typeUser") || "").trim(),
      pw: (formData.get("pw") || "").trim(),
    };
  }

  validate(payload) {
    if (!payload.username) return "El usuario es obligatorio.";
    if (!payload.fullname) return "El nombre completo es obligatorio.";
    if (!payload.typeUser) return "Selecciona el tipo de usuario.";
    if (!payload.pw) return "La contraseña es obligatoria.";
    return null;
  }

  getAuthHeader() {
    const token = localStorage.getItem("busy_token");
    const tokenType = localStorage.getItem("busy_token_type") || "bearer";
    if (!token) return null;
    return `${tokenType} ${token}`;
  }

  setStatus(message) {
    if (this.statusEl) this.statusEl.textContent = message || "";
  }
}
