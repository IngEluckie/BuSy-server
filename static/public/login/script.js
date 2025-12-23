const form = document.getElementById("loginForm");
const usernameEl = document.getElementById("username");
const passwordEl = document.getElementById("password");
const togglePwEl = document.getElementById("togglePw");
const submitBtn = document.getElementById("submitBtn");
const alertEl = document.getElementById("alert");

function setAlert(message) {
  if (!message) {
    alertEl.hidden = true;
    alertEl.textContent = "";
    return;
  }
  alertEl.hidden = false;
  alertEl.textContent = message;
}

togglePwEl?.addEventListener("click", () => {
  const isPassword = passwordEl.type === "password";
  passwordEl.type = isPassword ? "text" : "password";
  togglePwEl.textContent = isPassword ? "Ocultar" : "Mostrar";
  togglePwEl.setAttribute("aria-pressed", String(isPassword));
  passwordEl.focus();
});

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  setAlert("");

  const baseUrl = window.location.origin;
  const username = (usernameEl.value || "").trim();
  const password = passwordEl.value || "";
  if (!username || !password) {
    setAlert("Completa usuario y contraseña.");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Entrando…";

  try {
    const body = new URLSearchParams({ username, password });
    const res = await fetch(`${baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setAlert(data?.detail || "No se pudo iniciar sesión.");
      return;
    }

    if (data?.access_token) localStorage.setItem("busy_token", data.access_token);
    localStorage.setItem("busy_token_type", data?.token_type || "bearer");

    const tokenType = data?.token_type || "bearer";
    const token = data?.access_token;

    const meRes = await fetch(`${baseUrl}/auth/me`, {
      method: "GET",
      headers: { Authorization: `${tokenType} ${token}` },
    });
    const me = await meRes.json().catch(() => null);
    if (!meRes.ok) {
      setAlert(me?.detail || "No se pudo obtener tu información de usuario.");
      return;
    }

    localStorage.setItem("busy_user", JSON.stringify(me));
    localStorage.setItem("busy_user_fetched_at", String(Date.now()));

    const target = data?.dashboard || "/public/";
    window.location.href = new URL(target, baseUrl).toString();
  } catch (err) {
    setAlert("Error de red. Intenta de nuevo.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Entrar";
  }
});
