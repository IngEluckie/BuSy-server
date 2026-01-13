// static/public/userconf/modules/editUser.js

export default class EditUser {
  /**
   * @param {Object|string} options
   * - Si es string, se interpreta como username.
   * @param {HTMLElement|string} options.mount Punto de montaje (elemento o selector)
   * @param {string} [options.username] Usuario objetivo (si aplica)
   * @param {string} [options.apiBase] Base URL para endpoints (si aplica)
   * @param {Object} [options.initialData] Datos iniciales opcionales
   */
  constructor(options = {}) {
    const normalized =
      typeof options === "string" ? { username: options } : options || {};
    const { mount, username = null, apiBase = "/userconf", initialData = null } =
      normalized;

    this.apiBase = apiBase;
    this.mount = typeof mount === "string" ? document.querySelector(mount) : mount;
    this.username = username;
    this.state = {
      loading: false,
      saving: false,
      data: initialData,
      error: null,
    };

    this._abortController = null;
    this._bound = false;
  }

  // --- Ciclo de vida ---
  async init() {
    if (!this.mount) throw new Error("EditUser: mount no encontrado");
    this.render();
    this.bindEvents();
    await this.load();
  }

  destroy() {
    this.unbindEvents();
    this._abortController?.abort();
    this.mount.innerHTML = "";
  }

  // --- Render ---
  template() {
    const hasUser = Boolean(this.username);
    // Mantén esto como HTML string para que la clase "contenga el html"
    return `
      <section class="uc-module edit-user" aria-label="Editar usuario">
        <header class="edit-user__header">
          <h2>Editar usuario</h2>
          <p class="edit-user__subtitle">
            Usuario seleccionado:
            <strong data-role="selected-user">${hasUser ? this.escape(this.username) : "Ninguno"}</strong>
          </p>
        </header>

        <form class="edit-user__form" data-role="form">
          <div class="edit-user__field">
            <label for="eu-username">Usuario</label>
            <input id="eu-username" name="username" type="text" autocomplete="username" ${hasUser ? "" : "disabled"} />
          </div>

          <div class="edit-user__field">
            <label for="eu-fullname">Nombre completo</label>
            <input id="eu-fullname" name="fullname" type="text" autocomplete="name" ${hasUser ? "" : "disabled"} />
          </div>

          <div class="edit-user__field">
            <label for="eu-birthday">Cumpleaños</label>
            <input id="eu-birthday" name="birthday" type="date" autocomplete="bday" ${hasUser ? "" : "disabled"} />
          </div>

          <div class="edit-user__field">
            <label for="eu-rfc">RFC</label>
            <input id="eu-rfc" name="rfc" type="text" autocomplete="off" ${hasUser ? "" : "disabled"} />
          </div>

          <div class="edit-user__field">
            <label for="eu-cellphone">Celular</label>
            <input id="eu-cellphone" name="cellphone" type="tel" autocomplete="tel" ${hasUser ? "" : "disabled"} />
          </div>

          <div class="edit-user__field">
            <label for="eu-email">Email</label>
            <input id="eu-email" name="email" type="email" autocomplete="email" ${hasUser ? "" : "disabled"} />
          </div>

          <div class="edit-user__field">
            <label for="eu-type-user">Tipo de usuario</label>
            <select id="eu-type-user" name="typeUser" ${hasUser ? "" : "disabled"}>
              <option value="">Selecciona un tipo</option>
              <option value="1">superadmin</option>
              <option value="2">admin</option>
              <option value="3">manager</option>
              <option value="4">vendor</option>
              <option value="5">customer</option>
            </select>
          </div>

          <div class="edit-user__field">
            <label for="eu-password">Contraseña</label>
            <div class="edit-user__password">
              <input id="eu-password" name="pw" type="password" autocomplete="new-password" placeholder="******" ${hasUser ? "" : "disabled"} />
              <button type="button" class="uc-button" data-role="toggle-password" ${hasUser ? "" : "disabled"} aria-pressed="false">Ver</button>
            </div>
          </div>

          <div class="edit-user__actions">
            <button type="button" class="uc-button" data-role="reset" ${hasUser ? "" : "disabled"}>Reiniciar</button>
            <button type="submit" class="uc-button uc-button--primary" data-role="save" ${hasUser ? "" : "disabled"}>Guardar</button>
          </div>

          <p class="edit-user__status" data-role="status" aria-live="polite"></p>
        </form>
      </section>
    `;
  }

  render() {
    this.mount.innerHTML = this.template();
    this.cacheDom();
    this.syncFormFromState();
    this.setStatus("");
  }

  cacheDom() {
    this.form = this.mount.querySelector('[data-role="form"]');
    this.statusEl = this.mount.querySelector('[data-role="status"]');
    this.selectedUserEl = this.mount.querySelector('[data-role="selected-user"]');

    this.inputs = {
      username: this.mount.querySelector('#eu-username'),
      fullname: this.mount.querySelector('#eu-fullname'),
      birthday: this.mount.querySelector('#eu-birthday'),
      rfc: this.mount.querySelector('#eu-rfc'),
      cellphone: this.mount.querySelector('#eu-cellphone'),
      email: this.mount.querySelector('#eu-email'),
      typeUser: this.mount.querySelector('#eu-type-user'),
      pw: this.mount.querySelector('#eu-password'),
    };

    this.buttons = {
      reset: this.mount.querySelector('[data-role="reset"]'),
      save: this.mount.querySelector('[data-role="save"]'),
      togglePassword: this.mount.querySelector('[data-role="toggle-password"]'),
    };
  }

  // --- Eventos ---
  bindEvents() {
    if (this._bound) return;
    this._bound = true;

    this._onSubmit = (e) => {
      e.preventDefault();
      this.handleSave();
    };

    this._onReset = () => this.handleReset();
    this._onTogglePassword = () => this.togglePassword();

    this.form?.addEventListener("submit", this._onSubmit);
    this.buttons.reset?.addEventListener("click", this._onReset);
    this.buttons.togglePassword?.addEventListener("click", this._onTogglePassword);
  }

  unbindEvents() {
    if (!this._bound) return;
    this._bound = false;

    this.form?.removeEventListener("submit", this._onSubmit);
    this.buttons.reset?.removeEventListener("click", this._onReset);
    this.buttons.togglePassword?.removeEventListener("click", this._onTogglePassword);
  }

  // --- Data flow ---
  async load() {
    this.setLoading(true);
    try {
      // TODO: reemplazar por fetch real
      // this._abortController = new AbortController();
      // const res = await fetch(`${this.apiBase}/me`, { signal: this._abortController.signal });
      // const data = await res.json();

      const data = this.state.data ?? {
        username: this.username ?? "",
        fullname: "",
        birthday: "",
        rfc: "",
        cellphone: "",
        email: "",
        typeUser: "",
        pw: "",
      };

      this.state.data = data;
      this.syncFormFromState();
      this.setStatus("");
    } catch (err) {
      this.state.error = err;
      this.setStatus("No se pudo cargar la configuración.");
    } finally {
      this.setLoading(false);
    }
  }

  async handleSave() {
    if (this.state.saving) return;

    const payload = this.readForm();
    const validationError = this.validate(payload);
    if (validationError) {
      this.setStatus(validationError);
      return;
    }

    this.setSaving(true);
    try {
      const auth = this.getAuthHeader();
      if (!auth) {
        throw new Error("Necesitas iniciar sesión para guardar cambios.");
      }

      const baseUrl = window.location.origin;
      const encodedUserinfo = encodeURIComponent(JSON.stringify(payload));
      const url = `${baseUrl}${this.apiBase}/edit_user:${encodedUserinfo}`;

      const res = await fetch(url, {
        method: "POST",
        headers: { Authorization: auth },
      });

      const data = await res.json().catch(() => null);
      if (!res.ok) {
        const msg = data?.detail || "No se pudo guardar.";
        throw new Error(msg);
      }

      this.state.data = payload;
      this.setStatus(data?.message || "Guardado.");
    } catch (err) {
      this.state.error = err;
      this.setStatus(err?.message || "No se pudo guardar.");
    } finally {
      this.setSaving(false);
    }
  }

  handleReset() {
    this.syncFormFromState();
    this.setStatus("Reiniciado.");
  }

  // --- Form helpers ---
  readForm() {
    return {
      username: (this.inputs.username?.value ?? "").trim(),
      fullname: (this.inputs.fullname?.value ?? "").trim(),
      birthday: this.inputs.birthday?.value ?? "",
      rfc: (this.inputs.rfc?.value ?? "").trim(),
      cellphone: (this.inputs.cellphone?.value ?? "").trim(),
      email: (this.inputs.email?.value ?? "").trim(),
      typeUser: (this.inputs.typeUser?.value ?? "").trim(),
      pw: this.inputs.pw?.value ?? "",
    };
  }

  syncFormFromState() {
    const data = this.state.data || {};
    if (this.inputs.username) this.inputs.username.value = data.username ?? "";
    if (this.inputs.fullname) this.inputs.fullname.value = data.fullname ?? "";
    if (this.inputs.birthday) this.inputs.birthday.value = data.birthday ?? "";
    if (this.inputs.rfc) this.inputs.rfc.value = data.rfc ?? "";
    if (this.inputs.cellphone) this.inputs.cellphone.value = data.cellphone ?? "";
    if (this.inputs.email) this.inputs.email.value = data.email ?? "";
    if (this.inputs.typeUser) this.inputs.typeUser.value = data.typeUser ?? "";
    if (this.inputs.pw) this.inputs.pw.value = data.pw ?? "";
  }

  validate(payload) {
    // TODO: reglas reales
    if (!payload.username) return "El usuario es obligatorio.";
    return null;
  }

  getAuthHeader() {
    const token = localStorage.getItem("busy_token");
    const tokenType = localStorage.getItem("busy_token_type") || "bearer";
    if (!token) return null;
    return `${tokenType} ${token}`;
  }

  // --- UI state ---
  setLoading(isLoading) {
    this.state.loading = isLoading;
    this.form?.toggleAttribute("aria-busy", isLoading);
  }

  setSaving(isSaving) {
    this.state.saving = isSaving;
    if (this.buttons.save) this.buttons.save.disabled = isSaving;
  }

  setStatus(message) {
    if (this.statusEl) this.statusEl.textContent = message || "";
  }

  setUser(username) {
    this.username = username || null;
    if (this.selectedUserEl) {
      this.selectedUserEl.textContent = this.username || "Ninguno";
    }
    if (this.inputs.username) this.inputs.username.value = this.username || "";
    if (this.inputs.pw) this.inputs.pw.value = "";
    const disabled = !this.username;
    this.form?.toggleAttribute("data-disabled", disabled);
    Object.values(this.inputs).forEach((el) => {
      if (!el) return;
      el.disabled = disabled;
    });
    Object.values(this.buttons).forEach((el) => {
      if (!el) return;
      el.disabled = disabled;
    });
    this.setStatus(disabled ? "Selecciona un usuario para editar." : "");
  }

  setData(data) {
    if (!data) return;
    this.state.data = {
      username: this.username ?? "",
      fullname: "",
      birthday: "",
      rfc: "",
      cellphone: "",
      email: "",
      typeUser: "",
      pw: "",
      ...data,
    };
    this.syncFormFromState();
  }

  togglePassword() {
    if (!this.inputs.pw || !this.buttons.togglePassword) return;
    const isHidden = this.inputs.pw.type === "password";
    this.inputs.pw.type = isHidden ? "text" : "password";
    this.buttons.togglePassword.textContent = isHidden ? "Ocultar" : "Ver";
    this.buttons.togglePassword.setAttribute("aria-pressed", String(isHidden));
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
