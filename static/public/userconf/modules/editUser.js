// static/public/userconf/modules/editUser.js

export default class EditUser {
  /**
   * @param {Object} options
   * @param {HTMLElement|string} options.mount Punto de montaje (elemento o selector)
   * @param {string} [options.apiBase] Base URL para endpoints (si aplica)
   * @param {Object} [options.initialData] Datos iniciales opcionales
   */
  constructor({ mount, apiBase = "/userconf", initialData = null } = {}) {
    this.apiBase = apiBase;
    this.mount = typeof mount === "string" ? document.querySelector(mount) : mount;
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
    // Mantén esto como HTML string para que la clase "contenga el html"
    return `
      <section class="edit-user">
        <header class="edit-user__header">
          <h2>Configuración de usuario</h2>
          <p class="edit-user__subtitle">Edita tus preferencias</p>
        </header>

        <form class="edit-user__form" data-role="form">
          <div class="edit-user__field">
            <label for="eu-username">Usuario</label>
            <input id="eu-username" name="username" type="text" autocomplete="username" />
          </div>

          <div class="edit-user__field">
            <label for="eu-email">Email</label>
            <input id="eu-email" name="email" type="email" autocomplete="email" />
          </div>

          <div class="edit-user__field">
            <label for="eu-theme">Tema</label>
            <select id="eu-theme" name="theme">
              <option value="system">Sistema</option>
              <option value="light">Claro</option>
              <option value="dark">Oscuro</option>
            </select>
          </div>

          <div class="edit-user__actions">
            <button type="button" data-role="reset">Reiniciar</button>
            <button type="submit" data-role="save">Guardar</button>
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

    this.inputs = {
      username: this.mount.querySelector('#eu-username'),
      email: this.mount.querySelector('#eu-email'),
      theme: this.mount.querySelector('#eu-theme'),
    };

    this.buttons = {
      reset: this.mount.querySelector('[data-role="reset"]'),
      save: this.mount.querySelector('[data-role="save"]'),
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

    this.form?.addEventListener("submit", this._onSubmit);
    this.buttons.reset?.addEventListener("click", this._onReset);
  }

  unbindEvents() {
    if (!this._bound) return;
    this._bound = false;

    this.form?.removeEventListener("submit", this._onSubmit);
    this.buttons.reset?.removeEventListener("click", this._onReset);
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
        username: "",
        email: "",
        theme: "system",
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
      // TODO: reemplazar por fetch real
      // const res = await fetch(`${this.apiBase}/me`, {
      //   method: "PUT",
      //   headers: { "Content-Type": "application/json" },
      //   body: JSON.stringify(payload),
      // });
      // if (!res.ok) throw new Error("Save failed");

      this.state.data = payload;
      this.setStatus("Guardado.");
    } catch (err) {
      this.state.error = err;
      this.setStatus("No se pudo guardar.");
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
      email: (this.inputs.email?.value ?? "").trim(),
      theme: this.inputs.theme?.value ?? "system",
    };
  }

  syncFormFromState() {
    const data = this.state.data || {};
    if (this.inputs.username) this.inputs.username.value = data.username ?? "";
    if (this.inputs.email) this.inputs.email.value = data.email ?? "";
    if (this.inputs.theme) this.inputs.theme.value = data.theme ?? "system";
  }

  validate(payload) {
    // TODO: reglas reales
    if (!payload.username) return "El usuario es obligatorio.";
    if (!payload.email) return "El email es obligatorio.";
    return null;
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
}
