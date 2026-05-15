import EditUser from "../userconf/modules/editUser.js";
import AddUser from "../userconf/modules/addUser.js";
import DeleteUser from "../userconf/modules/deleteUser.js";
import GenerateBadge from "../userconf/modules/generateBadge.js";
import UploadDocumentation from "../userconf/modules/uploadDocumentation.js";

const icons = {
    layers: `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m12 3 9 5-9 5-9-5 9-5Z"/>
            <path d="m3 12 9 5 9-5M3 16l9 5 9-5"/>
        </svg>
    `,
    calendar: `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M8 2v4M16 2v4M3 10h18"/>
            <path d="M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z"/>
            <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"/>
        </svg>
    `,
    shield: `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/>
            <path d="m9 12 2 2 4-5"/>
        </svg>
    `,
    refresh: `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/>
            <path d="M3 12A9 9 0 0 1 18.5 5.8L21 8"/>
            <path d="M3 21v-5h5M21 3v5h-5"/>
        </svg>
    `,
    star: `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8-6.2-3.2L5.8 21 7 14.2 2 9.3l6.9-1L12 2Z"/>
        </svg>
    `,
    check: `
        <svg class="check-icon" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 6 9 17l-5-5"/>
        </svg>
    `,
    file: `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/>
            <path d="M14 2v6h6M10 13h4M10 17h4M8 13h.01M8 17h.01"/>
        </svg>
    `,
    user: `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <path d="M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z"/>
        </svg>
    `,
    backup: `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/>
            <path d="M14 2v6h6M12 18v-6M9 15l3 3 3-3"/>
        </svg>
    `,
    arrow: `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="m9 18 6-6-6-6"/>
        </svg>
    `
};

const sections = {
    system: {
        title: "Información del sistema",
        description: "Consulta el estado actual de Business System, versión instalada y próximas mejoras.",
        content: renderSystemSection
    },
    company: {
        title: "Datos de la empresa",
        description: "Administra la identidad visible del negocio y los datos base usados en documentos.",
        content: renderCompanySection
    },
    settings: {
        title: "Preferencias globales",
        description: "Define reglas generales que afectan la experiencia de todos los módulos.",
        cards: [
            ["Inventario estricto", "Evita ventas cuando no hay existencias disponibles."],
            ["Notificaciones internas", "Muestra avisos de actividad relevante en el panel principal."],
            ["Respaldos automáticos", "Programa copias locales de seguridad cada noche."]
        ],
        rows: [
            ["Modo operativo", "Producción"],
            ["Moneda predeterminada", "Peso mexicano (MXN)"],
            ["Formato de fecha", "15 mayo 2026"]
        ]
    },
    users: {
        title: "Administración de usuarios",
        description: "Administra altas, cambios, eliminaciones, gafetes y documentación de usuarios.",
        content: renderUsersSection
    },
    node: {
        title: "Configuración de nodo",
        description: "Administra la identidad, conexión y sincronización del nodo local.",
        cards: [
            ["Nodo local", "Define el identificador y estado operativo del nodo."],
            ["Conectividad", "Revisa parámetros de comunicación con otros servicios."],
            ["Sincronización", "Prepara reglas de intercambio entre nodos del sistema."]
        ],
        rows: [
            ["Estado del nodo", "Pendiente de configurar"],
            ["Última sincronización", "Sin registro disponible"],
            ["Modo de operación", "Local"]
        ]
    },
    wordpress: {
        title: "Wordpress Sync",
        description: "Gestiona la sincronización entre Business System y Wordpress.",
        cards: [
            ["Conexión Wordpress", "Configura el sitio y las credenciales de integración."],
            ["Catálogo", "Sincroniza productos, imágenes y disponibilidad."],
            ["Operaciones", "Monitorea tareas de publicación y actualización."]
        ],
        rows: [
            ["Estado de conexión", "Pendiente de configurar"],
            ["Última ejecución", "Sin registro disponible"],
            ["Sincronización automática", "No configurada"]
        ]
    }
};

const LOGIN_PATH = "/login/";
const COMPANY_PROFILE_ENDPOINT = "/systemconf/company-profile";
const SEARCH_USERS_ENDPOINT = "/userconf/search_byusername";
const USER_MODULES = {
    edit: EditUser,
    add: AddUser,
    delete: DeleteUser,
    badge: GenerateBadge,
    docs: UploadDocumentation
};
const COMPANY_FIELD_DEFAULTS = {
    legal_name: "",
    trade_name: "Business System Demo",
    rfc: "",
    tax_regime: "",
    email: "admin@business-system.local",
    phone: "+52 55 1234 5678",
    website: "https://business-system.local",
    street: "",
    exterior_number: "",
    interior_number: "",
    neighborhood: "",
    city: "Ciudad de México",
    state: "CDMX",
    country: "México",
    postal_code: "",
    logo_path: "",
    currency: "MXN",
    timezone: "America/Mexico_City",
    locale: "es-MX"
};

const sectionContent = document.querySelector("#sectionContent");
const tabButtons = document.querySelectorAll(".tab-button");
const saveButton = document.querySelector(".save-button");
const actionBar = document.querySelector(".action-bar");

let activeSectionKey = "system";
let companyProfile = null;
let companyRequestId = 0;
let activeUserModule = null;
const companyUi = {
    isLoading: false,
    isSaving: false,
    message: "Carga los datos registrados para editarlos.",
    kind: "info"
};
const userState = {
    activeView: "edit",
    selectedUsername: null,
    selectedUserInfo: null,
    searchRequestId: 0,
    selectedUserRequestId: 0
};

function getAuthHeader() {
    const token = localStorage.getItem("busy_token");
    const tokenType = localStorage.getItem("busy_token_type") || "bearer";
    if (!token) return null;
    return `${tokenType} ${token}`;
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
            ...(options.headers || {})
        }
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

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}

function getCompanyValue(key) {
    const value = companyProfile?.[key];
    if (value === undefined || value === null) return COMPANY_FIELD_DEFAULTS[key] || "";
    return value;
}

function setCompanyUi(message, kind = "info", state = {}) {
    companyUi.message = message;
    companyUi.kind = kind;
    companyUi.isLoading = Boolean(state.isLoading);
    companyUi.isSaving = Boolean(state.isSaving);

    const statusEl = document.querySelector("[data-company-status]");
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.dataset.kind = kind;
    }

    document.querySelectorAll(".company-field input").forEach((input) => {
        input.disabled = companyUi.isLoading || companyUi.isSaving;
    });

    if (saveButton) {
        saveButton.disabled = companyUi.isLoading || companyUi.isSaving;
    }
}

function renderActiveSection() {
    if (activeSectionKey !== "users") {
        destroyActiveUserModule();
    }

    const section = sections[activeSectionKey] || sections.system;
    sectionContent.innerHTML = section.content ? section.content() : renderSimpleSection(section);

    if (actionBar) {
        actionBar.hidden = activeSectionKey === "users";
    }

    if (activeSectionKey === "users") {
        initUsersSection();
        return;
    }

    if (activeSectionKey === "company") {
        setCompanyUi(companyUi.message, companyUi.kind, {
            isLoading: companyUi.isLoading,
            isSaving: companyUi.isSaving
        });
        return;
    }

    if (saveButton) {
        saveButton.disabled = false;
    }
}

function renderSystemSection() {
    return `
        <div class="section-grid">
            <div class="section-hero">
                <div class="section-copy">
                    <h2>Información del sistema</h2>
                    <p>Consulta el estado actual de Business System, versión instalada y próximas mejoras.</p>
                </div>

                <div class="summary-grid">
                    <article class="metric-card">
                        <span class="metric-icon">${icons.layers}</span>
                        <div>
                            <span class="metric-label">Versión actual</span>
                            <p class="metric-value">v1.0.0</p>
                            <span class="badge">Estable</span>
                        </div>
                    </article>
                    <article class="metric-card">
                        <span class="metric-icon green">${icons.calendar}</span>
                        <div>
                            <span class="metric-label">Última actualización</span>
                            <p class="metric-value">15 mayo 2026</p>
                            <span class="metric-label">Hace 3 días</span>
                        </div>
                    </article>
                    <article class="metric-card">
                        <span class="metric-icon purple">${icons.shield}</span>
                        <div>
                            <span class="metric-label">Estado del sistema</span>
                            <p class="metric-value">Operativo</p>
                            <span class="status-line"><i class="status-dot"></i> Todo funciona correctamente</span>
                        </div>
                    </article>
                </div>
            </div>

            <div class="panels-grid">
                <article class="panel">
                    <header class="panel-header">
                        <span class="panel-mark">${icons.refresh}</span>
                        <div>
                            <h3>Últimos parches</h3>
                            <p>Mejoras y correcciones recientes en el sistema.</p>
                        </div>
                    </header>
                    <ul class="item-list">
                        ${renderPatch("Corrección en cálculo de inventario por variantes", "Se corrigió un problema en el cálculo de existencias al trabajar con variantes de productos.", "12 mayo 2026")}
                        ${renderPatch("Mejora en carga de imágenes de artículos", "Optimización en la carga y visualización de imágenes para mayor rendimiento.", "08 mayo 2026")}
                        ${renderPatch("Optimización de búsqueda en tabla de productos", "Se mejoró la velocidad y precisión en la búsqueda de productos en el catálogo.", "02 mayo 2026")}
                    </ul>
                    <a class="panel-link" href="#">Ver historial completo ${icons.arrow}</a>
                </article>

                <article class="panel">
                    <header class="panel-header">
                        <span class="panel-mark purple">${icons.star}</span>
                        <div>
                            <h3>Próximas características</h3>
                            <p>Funciones y mejoras que estarán disponibles próximamente.</p>
                        </div>
                    </header>
                    <ul class="item-list">
                        ${renderUpcoming("Exportación de reportes en PDF", "Permite generar y descargar reportes en formato PDF de manera rápida y sencilla.", icons.file)}
                        ${renderUpcoming("Gestión avanzada de usuarios", "Nuevas opciones de roles, permisos y control de accesos más detallado.", icons.user)}
                        ${renderUpcoming("Módulo de respaldos automáticos", "Configuración de respaldos automáticos del sistema en intervalos programados.", icons.backup)}
                    </ul>
                    <a class="panel-link" href="#">Ver roadmap completo ${icons.arrow}</a>
                </article>
            </div>
        </div>
    `;
}

function renderPatch(title, description, date) {
    return `
        <li class="list-item">
            ${icons.check}
            <div class="item-copy">
                <strong>${title}</strong>
                <p>${description}</p>
            </div>
            <time class="item-date">${date}</time>
        </li>
    `;
}

function renderUpcoming(title, description, icon) {
    return `
        <li class="list-item upcoming">
            <span class="list-icon">${icon}</span>
            <div class="item-copy">
                <strong>${title}</strong>
                <p>${description}</p>
            </div>
            <span class="badge purple">Próximamente</span>
        </li>
    `;
}

const companyFieldGroups = [
    {
        title: "Identidad fiscal",
        description: "Datos legales usados en documentos, reportes y comprobantes.",
        fields: [
            ["Razón social", "legal_name", "Ej. Business System S.A. de C.V."],
            ["Nombre comercial", "trade_name", "Business System Demo"],
            ["RFC", "rfc", "Ej. BUS260515A10"],
            ["Régimen fiscal", "tax_regime", "Ej. Régimen General de Ley"]
        ]
    },
    {
        title: "Contacto",
        description: "Canales visibles para clientes, proveedores y documentos emitidos.",
        fields: [
            ["Correo electrónico", "email", "admin@business-system.local"],
            ["Teléfono", "phone", "+52 55 1234 5678"],
            ["Sitio web", "website", "https://business-system.local"]
        ]
    },
    {
        title: "Dirección",
        description: "Ubicación fiscal y operativa registrada para la empresa.",
        fields: [
            ["Calle", "street", "Ej. Avenida Principal"],
            ["Número exterior", "exterior_number", "Ej. 123"],
            ["Número interior", "interior_number", "Ej. Local 4"],
            ["Colonia", "neighborhood", "Ej. Centro"],
            ["Ciudad", "city", "Ciudad de México"],
            ["Estado", "state", "CDMX"],
            ["País", "country", "México"],
            ["Código postal", "postal_code", "Ej. 06000"]
        ]
    },
    {
        title: "Configuración regional",
        description: "Preferencias base para importes, idioma, fechas y horarios.",
        fields: [
            ["Moneda", "currency", "MXN"],
            ["Zona horaria", "timezone", "America/Mexico_City"],
            ["Idioma/región", "locale", "es-MX"]
        ]
    },
    {
        title: "Marca y documentos",
        description: "Recursos visuales usados en tickets, reportes y documentos del sistema.",
        fields: [
            ["Ruta del logotipo", "logo_path", "Ej. storage/images/logo.png"]
        ]
    }
];

function renderCompanySection() {
    const metadata = companyProfile
        ? `Actualizado: ${formatDateTime(companyProfile.updated_at)}`
        : "Esperando datos del sistema";

    return `
        <div class="company-layout">
            <div class="section-copy">
                <h2>Datos de la empresa</h2>
                <p>Administra la identidad visible del negocio y los datos base usados en documentos.</p>
            </div>

            <div class="company-summary-grid">
                <article class="simple-card">
                    <h3>Perfil activo</h3>
                    <p>Registro único de empresa vinculado a <strong>company_profile.id = 1</strong>.</p>
                </article>
                <article class="simple-card">
                    <h3>Datos fiscales</h3>
                    <p>Razón social, RFC y régimen fiscal listos para completar.</p>
                </article>
                <article class="simple-card">
                    <h3>Sincronización</h3>
                    <p>${metadata}</p>
                </article>
            </div>

            <form id="companyProfileForm" class="company-form">
                <div class="company-status" data-company-status data-kind="${companyUi.kind}">
                    ${escapeHtml(companyUi.message)}
                </div>
                <div class="company-panel-grid">
                    ${companyFieldGroups.map(renderCompanyGroup).join("")}
                </div>
            </form>
        </div>
    `;
}

function renderCompanyGroup(group) {
    return `
        <article class="company-panel">
            <header class="company-panel-header">
                <div>
                    <h3>${group.title}</h3>
                    <p>${group.description}</p>
                </div>
                <span class="value-chip">Editable</span>
            </header>
            <div class="company-field-grid">
                ${group.fields.map(([label, key, placeholder]) => `
                    <div class="company-field">
                        <label class="field-label" for="company-${key}">${label}</label>
                        <input
                            class="field-value"
                            id="company-${key}"
                            name="${key}"
                            type="${getCompanyInputType(key)}"
                            value="${escapeHtml(getCompanyValue(key))}"
                            placeholder="${escapeHtml(placeholder)}"
                            autocomplete="off"
                            ${companyUi.isLoading || companyUi.isSaving ? "disabled" : ""}
                        >
                        <code>${key}</code>
                    </div>
                `).join("")}
            </div>
        </article>
    `;
}

function getCompanyInputType(key) {
    if (key === "email") return "email";
    if (key === "website") return "url";
    if (key === "phone") return "tel";
    return "text";
}

function formatDateTime(value) {
    if (!value) return "sin fecha";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("es-MX", {
        dateStyle: "medium",
        timeStyle: "short"
    });
}

async function loadCompanyProfile() {
    const requestId = ++companyRequestId;
    setCompanyUi("Cargando datos de empresa...", "loading", { isLoading: true });

    try {
        const response = await apiFetch(COMPANY_PROFILE_ENDPOINT);
        const profile = await response.json();
        if (requestId !== companyRequestId || activeSectionKey !== "company") return;
        companyProfile = profile;
        companyUi.message = "Datos cargados. Puedes editar y guardar cambios.";
        companyUi.kind = "success";
        companyUi.isLoading = false;
        companyUi.isSaving = false;
        renderActiveSection();
    } catch (error) {
        if (requestId !== companyRequestId || activeSectionKey !== "company") return;
        setCompanyUi(error?.message || "No se pudieron cargar los datos de empresa.", "error");
    }
}

function collectCompanyPayload() {
    const form = document.querySelector("#companyProfileForm");
    if (!form) return null;

    const payload = {};
    companyFieldGroups.flatMap((group) => group.fields).forEach(([, key]) => {
        const input = form.elements[key];
        payload[key] = input ? input.value.trim() : "";
    });
    return payload;
}

async function saveCompanyProfile() {
    const payload = collectCompanyPayload();
    if (!payload) return;

    setCompanyUi("Guardando cambios...", "loading", { isSaving: true });

    try {
        const response = await apiFetch(COMPANY_PROFILE_ENDPOINT, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        companyProfile = await response.json();
        companyUi.message = "Datos de empresa guardados correctamente.";
        companyUi.kind = "success";
        companyUi.isLoading = false;
        companyUi.isSaving = false;
        renderActiveSection();
    } catch (error) {
        setCompanyUi(error?.message || "No se pudieron guardar los datos de empresa.", "error");
    }
}

function renderUsersSection() {
    return `
        <div class="users-settings">
            <div class="section-copy">
                <h2>Administración de usuarios</h2>
                <p>Busca usuarios y gestiona altas, cambios, eliminaciones, gafetes y documentación desde la configuración global.</p>
            </div>

            <div class="users-layout">
                <section class="users-panel users-search-panel" aria-label="Usuarios">
                    <div class="users-panel-header">
                        <label class="users-label" for="user-search">Buscar usuario</label>
                        <div class="users-search-row">
                            <input id="user-search" class="users-input" type="search" placeholder="Nombre, ID, correo..." autocomplete="off">
                            <button type="button" class="users-icon-button" id="user-search-btn" aria-label="Buscar">
                                <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                                    <path d="M10 4a6 6 0 1 0 4.47 10.03l4.25 4.25a1 1 0 0 0 1.41-1.41l-4.25-4.25A6 6 0 0 0 10 4Zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z"></path>
                                </svg>
                            </button>
                        </div>
                    </div>

                    <div class="user-list" id="user-list" role="listbox" aria-label="Resultados"></div>
                    <p class="hint" id="user-hint">Escribe para buscar usuarios.</p>
                </section>

                <section class="users-panel users-work-panel" aria-label="Funciones">
                    <nav class="function-tabs" aria-label="Funciones de usuario">
                        <button type="button" class="tab is-active" data-view="edit">Editar usuario</button>
                        <button type="button" class="tab" data-view="add">Agregar usuario</button>
                        <button type="button" class="tab" data-view="delete">Eliminar usuario</button>
                        <button type="button" class="tab" data-view="badge">Generar gafete</button>
                        <button type="button" class="tab" data-view="docs">Documentación</button>
                    </nav>

                    <section class="function-content" id="function-content" aria-live="polite">
                        <div id="module-root" class="module-root">
                            <div class="user-state">Selecciona una función para comenzar.</div>
                        </div>
                    </section>
                </section>
            </div>
        </div>
    `;
}

function initUsersSection() {
    userState.selectedUsername = null;
    userState.selectedUserInfo = null;
    renderUserListState("Escribe para buscar.", "info");

    document.querySelectorAll(".function-tabs .tab").forEach((tab) => {
        tab.addEventListener("click", () => setActiveUserTab(tab));
    });

    const defaultTab = document.querySelector(".function-tabs .tab.is-active");
    if (defaultTab) {
        setActiveUserTab(defaultTab);
    }

    const input = document.getElementById("user-search");
    const searchBtn = document.getElementById("user-search-btn");
    const debouncedSearch = debounce(runUserSearch, 250);

    input?.addEventListener("input", debouncedSearch);
    input?.addEventListener("search", runUserSearch);
    input?.addEventListener("keydown", (event) => {
        if (event.key === "Enter") runUserSearch();
    });
    searchBtn?.addEventListener("click", runUserSearch);
}

function destroyActiveUserModule() {
    try {
        activeUserModule?.destroy?.();
    } finally {
        activeUserModule = null;
    }
}

function setUserHint(message, kind = "info") {
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
    el.className = `user-state${kind === "loading" ? " is-loading" : ""}${kind === "error" ? " is-error" : ""}`;
    el.textContent = message;
    listEl.appendChild(el);
}

function renderUserModuleState(message, kind = "info") {
    const mountEl = document.getElementById("module-root");
    if (!mountEl) return;
    mountEl.innerHTML = "";

    const el = document.createElement("div");
    el.className = `user-state${kind === "loading" ? " is-loading" : ""}${kind === "error" ? " is-error" : ""}`;
    el.textContent = message;
    mountEl.appendChild(el);
}

async function mountUserModule(view) {
    const mountEl = document.getElementById("module-root");
    if (!mountEl) return;

    destroyActiveUserModule();

    const ModuleClass = USER_MODULES[view] || EditUser;
    activeUserModule = new ModuleClass({
        mount: mountEl,
        username: userState.selectedUsername
    });

    try {
        await activeUserModule.init();
        activeUserModule?.setUser?.(userState.selectedUsername);
        if (userState.selectedUserInfo) {
            activeUserModule?.setData?.(userState.selectedUserInfo);
        }
    } catch (error) {
        renderUserModuleState(error?.message || "No se pudo cargar el módulo.", "error");
    }
}

function setActiveUserTab(nextTab) {
    const tabs = document.querySelectorAll(".function-tabs .tab");
    tabs.forEach((tab) => tab.classList.toggle("is-active", tab === nextTab));
    userState.activeView = nextTab?.dataset?.view || "edit";
    mountUserModule(userState.activeView);
}

async function setSelectedUser(nextItem) {
    const items = document.querySelectorAll(".user-list .user-item");
    items.forEach((item) => {
        const selected = item === nextItem;
        item.classList.toggle("is-selected", selected);
        item.setAttribute("aria-selected", selected ? "true" : "false");
    });

    userState.selectedUsername = nextItem?.dataset?.username || null;
    userState.selectedUserInfo = null;
    const requestId = ++userState.selectedUserRequestId;

    if (userState.selectedUsername) {
        setUserHint(`Usuario seleccionado: ${userState.selectedUsername}`, "info");
    }

    activeUserModule?.setUser?.(userState.selectedUsername);
    if (!userState.selectedUsername) return;

    activeUserModule?.setLoading?.(true);
    try {
        const data = await fetchUserInfo(userState.selectedUsername);
        if (requestId !== userState.selectedUserRequestId) return;
        if (!data) {
            setUserHint("No se encontró información del usuario.", "error");
            activeUserModule?.setStatus?.("No se encontró información del usuario.");
            return;
        }
        userState.selectedUserInfo = data;
        activeUserModule?.setData?.(data);
    } catch (error) {
        if (requestId !== userState.selectedUserRequestId) return;
        const message = error?.message || "No se pudo cargar la información.";
        setUserHint(message, "error");
        activeUserModule?.setStatus?.(message);
    } finally {
        if (requestId === userState.selectedUserRequestId) {
            activeUserModule?.setLoading?.(false);
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
    userState.selectedUsername = null;
    userState.selectedUserInfo = null;

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
    const auth = getAuthHeader();
    if (!auth) {
        throw new Error("Necesitas iniciar sesión para buscar usuarios.");
    }

    const url = new URL(`${window.location.origin}${SEARCH_USERS_ENDPOINT}/${encodeURIComponent(username)}`);
    url.searchParams.set("limit", String(limit));

    const response = await fetch(url.toString(), {
        method: "GET",
        headers: { Authorization: auth }
    });

    if (response.status === 401) {
        setUserHint("Sesión expirada. Redirigiendo a login...", "error");
        setTimeout(() => {
            window.location.href = new URL(LOGIN_PATH, window.location.origin).toString();
        }, 400);
        return [];
    }

    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(data?.detail || "No se pudo buscar usuarios.");
    }

    return Array.isArray(data) ? data : [];
}

async function fetchUserInfo(username) {
    const auth = getAuthHeader();
    if (!auth) {
        throw new Error("Necesitas iniciar sesión para ver la información.");
    }

    const url = new URL(`${window.location.origin}/userconf/get_userinfo/${encodeURIComponent(username)}`);
    const response = await fetch(url.toString(), {
        method: "GET",
        headers: { Authorization: auth }
    });

    if (response.status === 401) {
        setUserHint("Sesión expirada. Redirigiendo a login...", "error");
        setTimeout(() => {
            window.location.href = new URL(LOGIN_PATH, window.location.origin).toString();
        }, 400);
        return null;
    }

    const data = await response.json().catch(() => null);
    if (!response.ok) {
        throw new Error(data?.detail || "No se pudo cargar la información del usuario.");
    }

    return data;
}

function debounce(fn, delayMs) {
    let timeoutId = null;
    return (...args) => {
        if (timeoutId) window.clearTimeout(timeoutId);
        timeoutId = window.setTimeout(() => fn(...args), delayMs);
    };
}

async function runUserSearch() {
    const input = document.getElementById("user-search");
    const query = (input?.value || "").trim();
    const requestId = ++userState.searchRequestId;

    if (!query) {
        userState.selectedUsername = null;
        userState.selectedUserInfo = null;
        setUserHint("Escribe para buscar usuarios.", "info");
        renderUserListState("Escribe para buscar.", "info");
        activeUserModule?.setUser?.(userState.selectedUsername);
        return;
    }

    setUserHint("Buscando...", "info");
    renderUserListState("Buscando...", "loading");

    try {
        const usernames = await searchUsers(query);
        if (requestId !== userState.searchRequestId) return;
        renderUserList(usernames);
        setUserHint(usernames.length ? `Resultados: ${usernames.length}` : "Sin resultados.", "info");
    } catch (error) {
        if (requestId !== userState.searchRequestId) return;
        const message = error?.message || "Error al buscar usuarios.";
        setUserHint(message, "error");
        renderUserListState(message, "error");
    }
}

function renderSimpleSection(section) {
    return `
        <div class="simple-layout">
            <div class="section-copy">
                <h2>${section.title}</h2>
                <p>${section.description}</p>
            </div>

            <div class="simple-grid">
                ${section.cards.map(([title, description]) => `
                    <article class="simple-card">
                        <h3>${title}</h3>
                        <p>${description}</p>
                    </article>
                `).join("")}
            </div>

            <article class="panel">
                <header class="panel-header">
                    <span class="panel-mark">${icons.layers}</span>
                    <div>
                        <h3>Resumen de configuración</h3>
                        <p>Valores simulados para representar la estructura visual de esta sección.</p>
                    </div>
                </header>
                <div>
                    ${section.rows.map(([label, value]) => `
                        <div class="setting-row">
                            <div class="item-copy">
                                <strong>${label}</strong>
                                <p>${value}</p>
                            </div>
                            <span class="value-chip">Configurado</span>
                        </div>
                    `).join("")}
                </div>
            </article>
        </div>
    `;
}

function setActiveSection(sectionKey) {
    const section = sections[sectionKey] || sections.system;
    activeSectionKey = sectionKey;

    tabButtons.forEach((button) => {
        const isActive = button.dataset.section === sectionKey;
        button.classList.toggle("is-active", isActive);
        button.setAttribute("aria-pressed", String(isActive));
    });

    renderActiveSection();

    if (sectionKey === "company") {
        loadCompanyProfile();
    }
}

tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
        setActiveSection(button.dataset.section);
    });
});

saveButton?.addEventListener("click", () => {
    if (activeSectionKey === "company") {
        saveCompanyProfile();
        return;
    }
});

window.addEventListener("userconf:deleted", (event) => {
    const deletedUsername = event?.detail?.username;
    if (!deletedUsername) return;

    removeUserFromList(deletedUsername);
    if (userState.selectedUsername === deletedUsername) {
        userState.selectedUsername = null;
        userState.selectedUserInfo = null;
        setUserHint("Usuario eliminado.", "info");
        activeUserModule?.setUser?.(null);
    }
});

setActiveSection("system");
