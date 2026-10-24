"use strict";

const state = { user: null, categories: [] };

/* ---------- Köməkçi funksiyalar ---------- */

// XSS-dən qorunma: istifadəçi məlumatı HTML-ə yazılmazdan əvvəl escape olunur
function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

async function api(path, { method = "GET", body } = {}) {
  const options = { method, headers: {}, credentials: "same-origin" };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch("/api" + path, options);
  } catch (_) {
    throw new ApiError("Serverlə əlaqə qurulmadı. İnternet bağlantısını yoxlayın.", 0, {});
  }
  let data = null;
  try { data = await response.json(); } catch (_) { /* boş cavab */ }
  if (!response.ok) {
    throw new ApiError((data && data.error) || "Xəta baş verdi", response.status,
                       (data && data.details) || {});
  }
  return data;
}

class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

function toast(message, isError = false) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = "toast" + (isError ? " error" : "");
  el.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { el.hidden = true; }, 3500);
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function showFormErrors(form, error) {
  form.querySelectorAll(".field-error").forEach((n) => n.remove());
  const box = form.querySelector("#formError");
  box.textContent = error.message;
  for (const [field, message] of Object.entries(error.details || {})) {
    const input = form.querySelector(`[name="${field}"]`);
    if (input) {
      const span = document.createElement("span");
      span.className = "field-error";
      span.textContent = message;
      input.parentElement.appendChild(span);
    }
  }
}

function formatDate(iso) {
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

/* ---------- Naviqasiya ---------- */

async function loadUser() {
  try {
    state.user = await api("/auth/me");
  } catch (_) {
    state.user = null;
  }
  renderNav();
}

function renderNav() {
  const nav = document.getElementById("nav");
  const u = state.user;
  let html = '<a href="/">Tədbirlər</a>';
  if (u && u.role === "admin") html += '<a href="/dashboard">Panel</a>';
  if (u) {
    html += `<span>${esc(u.full_name)}</span><button id="logoutBtn">Çıxış</button>`;
  } else {
    html += '<a href="/login">Giriş</a><a href="/register">Qeydiyyat</a>';
  }
  nav.innerHTML = html;
  const btn = document.getElementById("logoutBtn");
  if (btn) {
    btn.addEventListener("click", async () => {
      await api("/auth/logout", { method: "POST" });
      location.href = "/";
    });
  }
}

async function loadCategories() {
  state.categories = await api("/categories");
}

function fillCategorySelect(select) {
  for (const c of state.categories) {
    const option = document.createElement("option");
    option.value = c.id;
    option.textContent = c.name;
    select.appendChild(option);
  }
}

/* ---------- Tədbirlər siyahısı ---------- */

function eventCard(e) {
  const percent = Math.min(100, Math.round((e.registered_count / e.max_participants) * 100));
  const status = e.is_past
    ? '<span class="badge past">Keçmiş</span>'
    : '<span class="badge upcoming">Gələcək</span>';
  const full = e.is_full && !e.is_past ? ' <span class="badge full">Limit dolub</span>' : "";

  let buttons = `<a class="btn" href="/events/${e.id}">Ətraflı</a>`;
  if (state.user && !e.is_past) {
    if (e.is_registered) {
      buttons += `<button class="btn" data-action="cancel" data-id="${e.id}">Qeydiyyatı ləğv et</button>`;
    } else if (e.is_full) {
      buttons += '<button class="btn" disabled>Limit dolub</button>';
    } else {
      buttons += `<button class="btn primary" data-action="register" data-id="${e.id}">Qeydiyyatdan keç</button>`;
    }
  }
  if (state.user && state.user.role === "admin") {
    buttons += `<a class="btn" href="/events/${e.id}/edit">Redaktə</a>` +
               `<button class="btn danger" data-action="delete" data-id="${e.id}">Sil</button>`;
  }

  return `<article class="card event-card">
    <span class="badge">${esc(e.category_name)}</span> ${status}${full}
    <h3>${esc(e.title)}</h3>
    <p class="meta">📅 ${formatDate(e.event_date)} · ${esc(e.event_time)}</p>
    <p class="meta">📍 ${esc(e.location)}</p>
    <p class="meta">👥 ${e.registered_count} / ${e.max_participants} iştirakçı</p>
    <div class="bar"><span style="width:${percent}%"></span></div>
    <div class="actions">${buttons}</div>
  </article>`;
}

async function loadEvents() {
  const form = document.getElementById("filterForm");
  const params = new URLSearchParams();
  for (const [key, value] of new FormData(form).entries()) {
    if (value) params.set(key, value);
  }
  const container = document.getElementById("events");
  try {
    const events = await api("/events?" + params.toString());
    container.innerHTML = events.length
      ? events.map(eventCard).join("")
      : '<div class="empty">Axtarışa uyğun tədbir tapılmadı.</div>';
  } catch (error) {
    container.innerHTML = `<div class="empty">${esc(error.message)}</div>`;
  }
}

async function handleEventAction(event) {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = button.dataset.id;
  try {
    if (button.dataset.action === "register") {
      await api(`/events/${id}/register`, { method: "POST" });
      toast("Qeydiyyat uğurla tamamlandı");
    } else if (button.dataset.action === "cancel") {
      await api(`/events/${id}/register`, { method: "DELETE" });
      toast("Qeydiyyat ləğv edildi");
    } else if (button.dataset.action === "delete") {
      if (!confirm("Bu tədbiri silmək istədiyinizə əminsiniz?")) return;
      await api(`/events/${id}`, { method: "DELETE" });
      toast("Tədbir silindi");
    }
    await loadEvents();
  } catch (error) {
    toast(error.message, true);
    if (error.status === 401) setTimeout(() => { location.href = "/login"; }, 1200);
    else await loadEvents();
  }
}

async function initIndex() {
  await loadCategories();
  const form = document.getElementById("filterForm");
  fillCategorySelect(form.elements.category_id);
  if (state.user && state.user.role === "admin") {
    document.getElementById("newEventBtn").hidden = false;
  }
  let timer;
  form.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(loadEvents, 250); });
  form.addEventListener("change", loadEvents);
  form.addEventListener("reset", () => setTimeout(loadEvents, 0));
  form.addEventListener("submit", (e) => { e.preventDefault(); loadEvents(); });
  document.getElementById("events").addEventListener("click", handleEventAction);
  await loadEvents();
}

/* ---------- Giriş / qeydiyyat ---------- */

function initAuthForm(formId, path) {
  const form = document.getElementById(formId);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api(path, { method: "POST", body: formData(form) });
      location.href = "/";
    } catch (error) {
      showFormErrors(form, error);
    }
  });
}

/* ---------- Tədbir formu (yaratma / redaktə) ---------- */

async function initEventForm() {
  const form = document.getElementById("eventForm");
  const eventId = form.dataset.eventId;
  if (!state.user || state.user.role !== "admin") {
    form.innerHTML = '<p>Bu səhifə yalnız administrator üçündür. <a href="/login">Giriş</a></p>';
    return;
  }
  await loadCategories();
  fillCategorySelect(form.elements.category_id);

  if (eventId) {
    try {
      const e = await api(`/events/${eventId}`);
      for (const name of ["title", "description", "category_id", "event_date", "event_time",
                          "location", "max_participants"]) {
        form.elements[name].value = e[name];
      }
    } catch (error) {
      toast(error.message, true);
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api(eventId ? `/events/${eventId}` : "/events",
                { method: eventId ? "PUT" : "POST", body: formData(form) });
      location.href = "/";
    } catch (error) {
      showFormErrors(form, error);
    }
  });
}

/* ---------- Tədbir səhifəsi ---------- */

async function initEventDetail() {
  const box = document.getElementById("eventDetail");
  const id = box.dataset.eventId;
  try {
    const e = await api(`/events/${id}`);
    box.innerHTML = `
      <span class="badge">${esc(e.category_name)}</span>
      <span class="badge ${e.is_past ? "past" : "upcoming"}">${e.is_past ? "Keçmiş" : "Gələcək"}</span>
      <h1>${esc(e.title)}</h1>
      <p>${esc(e.description) || "<em>Təsvir yoxdur</em>"}</p>
      <p class="meta">📅 ${formatDate(e.event_date)} · ${esc(e.event_time)}</p>
      <p class="meta">📍 ${esc(e.location)}</p>
      <p class="meta">👥 Qeydiyyatdan keçən: <strong>${e.registered_count}</strong> / ${e.max_participants}
        (boş yer: ${e.seats_left})</p>
      <div class="actions"><a class="btn" href="/">← Siyahı</a></div>`;
  } catch (error) {
    box.innerHTML = `<p>${esc(error.message)}</p><a class="btn" href="/">Ana səhifə</a>`;
    return;
  }

  if (state.user && state.user.role === "admin") {
    document.getElementById("participantsSection").hidden = false;
    document.getElementById("exportBtn").href = `/api/events/${id}/export`;
    const list = await api(`/events/${id}/participants`);
    document.getElementById("participants").innerHTML = list.length
      ? `<table><thead><tr><th>№</th><th>Ad və soyad</th><th>E-poçt</th><th>Vaxt</th></tr></thead><tbody>` +
        list.map((p, i) => `<tr><td>${i + 1}</td><td>${esc(p.full_name)}</td><td>${esc(p.email)}</td>
          <td>${esc(p.registered_at)}</td></tr>`).join("") + "</tbody></table>"
      : "<p>Hələ qeydiyyat yoxdur.</p>";
  }
}

/* ---------- İdarəetmə paneli ---------- */

function statBar(label, value, max, suffix = "") {
  const percent = max ? Math.round((value / max) * 100) : 0;
  return `<div class="stat-row"><div class="label"><span>${esc(label)}</span>
    <strong>${value}${suffix}</strong></div><div class="bar"><span style="width:${percent}%"></span></div></div>`;
}

async function initDashboard() {
  const tiles = document.getElementById("tiles");
  if (!state.user || state.user.role !== "admin") {
    tiles.innerHTML = '<div class="card">Bu səhifə yalnız administrator üçündür. <a href="/login">Giriş</a></div>';
    return;
  }
  try {
    const s = await api("/stats");
    tiles.innerHTML = [
      ["Tədbirlərin ümumi sayı", s.total_events],
      ["Qeydiyyatların ümumi sayı", s.total_registrations],
      ["İstifadəçilərin sayı", s.total_users],
    ].map(([l, n]) => `<div class="tile"><div class="num">${n}</div><div>${l}</div></div>`).join("");

    document.getElementById("topEvents").innerHTML = s.top_events.length
      ? s.top_events.map((e) => statBar(e.title, e.registered_count, e.max_participants,
          ` / ${e.max_participants}`)).join("")
      : "<p>Məlumat yoxdur.</p>";

    const maxEvents = Math.max(1, ...s.by_category.map((c) => c.event_count));
    document.getElementById("byCategory").innerHTML =
      `<table><thead><tr><th>Kateqoriya</th><th>Tədbir</th><th>Qeydiyyat</th></tr></thead><tbody>` +
      s.by_category.map((c) => `<tr><td>${esc(c.category)}</td><td>${c.event_count}</td>
        <td>${c.registration_count}</td></tr>`).join("") + "</tbody></table>" +
      '<div style="margin-top:16px">' +
      s.by_category.map((c) => statBar(c.category, c.event_count, maxEvents)).join("") + "</div>";
  } catch (error) {
    tiles.innerHTML = `<div class="card">${esc(error.message)}</div>`;
  }
}

/* ---------- Başlanğıc ---------- */

document.addEventListener("DOMContentLoaded", async () => {
  await loadUser();
  const page = document.body.dataset.page;
  if (page === "index") await initIndex();
  else if (page === "login") initAuthForm("loginForm", "/auth/login");
  else if (page === "register") initAuthForm("registerForm", "/auth/register");
  else if (page === "event_form") await initEventForm();
  else if (page === "event_detail") await initEventDetail();
  else if (page === "dashboard") await initDashboard();
});
