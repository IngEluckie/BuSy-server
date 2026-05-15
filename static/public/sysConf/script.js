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
        description: "Revisa el estado general de accesos, roles y permisos del sistema.",
        cards: [
            ["Administradores", "2 usuarios con control total del sistema."],
            ["Operadores", "8 cuentas activas para ventas, almacén y reportes."],
            ["Invitaciones", "1 invitación pendiente de activación."]
        ],
        rows: [
            ["Política de acceso", "Contraseña obligatoria para todas las cuentas"],
            ["Última revisión", "14 mayo 2026"],
            ["Estado", "Permisos sincronizados"]
        ]
    }
};

const sectionContent = document.querySelector("#sectionContent");
const tabButtons = document.querySelectorAll(".tab-button");

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
            ["Razón social", "legal_name", "Pendiente de capturar"],
            ["Nombre comercial", "trade_name", "Business System Demo"],
            ["RFC", "rfc", "Pendiente de capturar"],
            ["Régimen fiscal", "tax_regime", "Pendiente de capturar"]
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
            ["Calle", "street", "Pendiente de capturar"],
            ["Número exterior", "exterior_number", "Pendiente"],
            ["Número interior", "interior_number", "Sin interior"],
            ["Colonia", "neighborhood", "Pendiente de capturar"],
            ["Ciudad", "city", "Ciudad de México"],
            ["Estado", "state", "CDMX"],
            ["País", "country", "México"],
            ["Código postal", "postal_code", "Pendiente"]
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
            ["Ruta del logotipo", "logo_path", "Pendiente de cargar"]
        ]
    }
];

function renderCompanySection() {
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
                    <h3>Uso documental</h3>
                    <p>Estos espacios alimentarán tickets, reportes, respaldos y formatos impresos.</p>
                </article>
            </div>

            <div class="company-panel-grid">
                ${companyFieldGroups.map(renderCompanyGroup).join("")}
            </div>
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
                <span class="value-chip">Mock</span>
            </header>
            <div class="company-field-grid">
                ${group.fields.map(([label, key, value]) => `
                    <div class="company-field">
                        <span class="field-label">${label}</span>
                        <strong class="field-value">${value}</strong>
                        <code>${key}</code>
                    </div>
                `).join("")}
            </div>
        </article>
    `;
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

    tabButtons.forEach((button) => {
        const isActive = button.dataset.section === sectionKey;
        button.classList.toggle("is-active", isActive);
        button.setAttribute("aria-pressed", String(isActive));
    });

    sectionContent.innerHTML = section.content ? section.content() : renderSimpleSection(section);
}

tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
        setActiveSection(button.dataset.section);
    });
});

setActiveSection("system");
