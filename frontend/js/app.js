/* Group 15 Airline — auth module frontend logic (vanilla JS) */

/* ---- Theme: persist choice, default light -------------------------------- */
(function initTheme() {
  const saved = localStorage.getItem("g15-theme") || "light";
  document.documentElement.setAttribute("data-theme", saved);
})();

function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute("data-theme") === "light" ? "dark" : "light";
  html.setAttribute("data-theme", next);
  localStorage.setItem("g15-theme", next);
  const label = document.querySelector(".theme-toggle .label");
  if (label) label.textContent = next === "light" ? "Dark" : "Light";
}

/* ---- Small helpers ------------------------------------------------------- */
async function api(path, body, method = "POST") {
  const options = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) options.body = JSON.stringify(body);

  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Something went wrong.");
  return data;
}

function showAlert(el, message, type) {
  el.textContent = message;
  el.className = "alert show " + type;
}
function clearAlert(el) { el.className = "alert"; }

/* ---- My Bookings / RES-02 cancellation ---------------------------------- */
let bookingsLoaded = false;
let activeBookingsTab = "ongoing";
let bookingPendingCancellation = null;
const bookingsState = { ongoing: [], cancelled: [] };

function formatRoute(booking) {
  return `${booking.origin} to ${booking.destination}`;
}

function createCell(text) {
  const cell = document.createElement("td");
  cell.textContent = text || "-";
  return cell;
}

function renderBookingsTable(bookings, panel, type) {
  panel.innerHTML = "";

  if (!bookings.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = type === "ongoing"
      ? "No ongoing bookings are available."
      : "No cancelled bookings are available.";
    panel.appendChild(empty);
    return;
  }

  const wrap = document.createElement("div");
  wrap.className = "booking-table-wrap";
  const table = document.createElement("table");
  table.className = "bookings-table";

  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  ["Booking", "Passenger", "Flight", "Route", "Departure", "Status", "Details"].forEach((label) => {
    const th = document.createElement("th");
    th.textContent = label;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);

  const tbody = document.createElement("tbody");
  bookings.forEach((booking) => {
    const row = document.createElement("tr");
    row.appendChild(createCell(`#${booking.id}`));
    row.appendChild(createCell(booking.passenger_name));
    row.appendChild(createCell(booking.flight_number));
    row.appendChild(createCell(formatRoute(booking)));
    row.appendChild(createCell(booking.departure_date));

    const statusCell = document.createElement("td");
    const status = document.createElement("span");
    status.className = `status-pill ${booking.status.toLowerCase()}`;
    status.textContent = booking.status;
    statusCell.appendChild(status);
    row.appendChild(statusCell);

    const detailCell = document.createElement("td");
    if (type === "ongoing") {
      const cancelButton = document.createElement("button");
      cancelButton.type = "button";
      cancelButton.className = "btn btn-danger btn-small";
      cancelButton.textContent = "Cancel";
      cancelButton.addEventListener("click", () => openCancelModal(booking));
      detailCell.appendChild(cancelButton);
    } else {
      const code = document.createElement("span");
      code.className = "verification-code";
      code.textContent = booking.verification_code || "-";
      detailCell.appendChild(code);

      const cancelledAt = document.createElement("div");
      cancelledAt.textContent = `Cancelled: ${booking.cancellation_timestamp || "-"}`;
      detailCell.appendChild(cancelledAt);
    }
    row.appendChild(detailCell);
    tbody.appendChild(row);
  });

  table.appendChild(thead);
  table.appendChild(tbody);
  wrap.appendChild(table);
  panel.appendChild(wrap);
}

function setBookingsTab(tab) {
  activeBookingsTab = tab;

  const ongoingTab = document.getElementById("ongoingBookingsTab");
  const cancelledTab = document.getElementById("cancelledBookingsTab");
  const ongoingPanel = document.getElementById("ongoingBookingsPanel");
  const cancelledPanel = document.getElementById("cancelledBookingsPanel");

  ongoingTab.classList.toggle("active", tab === "ongoing");
  cancelledTab.classList.toggle("active", tab === "cancelled");
  ongoingTab.setAttribute("aria-selected", tab === "ongoing" ? "true" : "false");
  cancelledTab.setAttribute("aria-selected", tab === "cancelled" ? "true" : "false");
  ongoingPanel.hidden = tab !== "ongoing";
  cancelledPanel.hidden = tab !== "cancelled";

  renderBookingsTable(bookingsState.ongoing, ongoingPanel, "ongoing");
  renderBookingsTable(bookingsState.cancelled, cancelledPanel, "cancelled");
}

async function loadBookings() {
  const alert = document.getElementById("bookingsAlert");
  try {
    const [ongoing, cancelled] = await Promise.all([
      api("/api/bookings/ongoing", undefined, "GET"),
      api("/api/bookings/cancelled", undefined, "GET"),
    ]);
    bookingsState.ongoing = ongoing;
    bookingsState.cancelled = cancelled;
    bookingsLoaded = true;
    setBookingsTab(activeBookingsTab);
  } catch (err) {
    showAlert(alert, err.message, "error");
  }
}

async function showBookings() {
  const section = document.getElementById("bookingsSection");
  const alert = document.getElementById("bookingsAlert");
  if (!section) return;

  section.hidden = false;
  clearAlert(alert);
  if (!bookingsLoaded) await loadBookings();
  section.scrollIntoView({ behavior: "smooth", block: "start" });
}

function openCancelModal(booking) {
  bookingPendingCancellation = booking;

  const modal = document.getElementById("cancelBookingModal");
  const summary = document.getElementById("cancelBookingSummary");
  const emailInput = document.getElementById("cancelAccountEmail");
  const alert = document.getElementById("cancelModalAlert");

  summary.textContent = `To cancel booking #${booking.id} for flight ${booking.flight_number}, re-enter the account email for this reservation.`;
  emailInput.value = "";
  clearAlert(alert);
  modal.hidden = false;
  emailInput.focus();
}

function closeCancelModal() {
  const modal = document.getElementById("cancelBookingModal");
  if (modal) modal.hidden = true;
  bookingPendingCancellation = null;
}

function wireBookings() {
  const section = document.getElementById("bookingsSection");
  if (!section) return;

  const nav = document.getElementById("myBookingsNav");
  const tile = document.getElementById("myBookingsTile");
  const ongoingTab = document.getElementById("ongoingBookingsTab");
  const cancelledTab = document.getElementById("cancelledBookingsTab");
  const closeBtn = document.getElementById("closeCancelModal");
  const form = document.getElementById("cancelBookingForm");

  if (nav) nav.addEventListener("click", (e) => { e.preventDefault(); showBookings(); });
  if (tile) {
    tile.addEventListener("click", showBookings);
    tile.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        showBookings();
      }
    });
  }
  ongoingTab.addEventListener("click", () => setBookingsTab("ongoing"));
  cancelledTab.addEventListener("click", () => setBookingsTab("cancelled"));
  closeBtn.addEventListener("click", closeCancelModal);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!bookingPendingCancellation) return;

    const emailInput = document.getElementById("cancelAccountEmail");
    const modalAlert = document.getElementById("cancelModalAlert");
    const pageAlert = document.getElementById("bookingsAlert");
    const confirmBtn = document.getElementById("confirmCancelBtn");

    clearAlert(modalAlert);
    confirmBtn.disabled = true;
    try {
      const data = await api(`/api/bookings/${bookingPendingCancellation.id}/cancel`, {
        account_email: emailInput.value,
      }, "PUT");
      closeCancelModal();
      showAlert(pageAlert, data.message, "success");
      await loadBookings();
      setBookingsTab("cancelled");
    } catch (err) {
      showAlert(modalAlert, err.message, "error");
    } finally {
      confirmBtn.disabled = false;
    }
  });
}

/* ---- Login screen -------------------------------------------------------- */
function wireLogin() {
  const form = document.getElementById("loginForm");
  if (!form) return;
  const alert = document.getElementById("alert");
  const btn = document.getElementById("submitBtn");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert(alert);
    btn.disabled = true;
    try {
      const data = await api("/api/login", {
        email: document.getElementById("email").value,
        password: document.getElementById("password").value,
      });
      // Route exactly like the example: no profile yet -> Profile Setup.
      window.location.href = data.next_screen === "profile"
        ? "profile.html" : "dashboard.html";
    } catch (err) {
      showAlert(alert, err.message, "error");
      btn.disabled = false;
    }
  });
}

/* ---- Sign up screen ------------------------------------------------------ */
function wireSignup() {
  const form = document.getElementById("signupForm");
  if (!form) return;
  const alert = document.getElementById("alert");
  const btn = document.getElementById("submitBtn");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert(alert);
    const pw = document.getElementById("password").value;
    const cpw = document.getElementById("confirm").value;

    // Client-side checks first (server re-validates regardless).
    if (pw !== cpw) return showAlert(alert, "The passwords entered do not match.", "error");
    if (pw.length < 8) return showAlert(alert, "Password must be at least 8 characters.", "error");

    btn.disabled = true;
    try {
      await api("/api/register", {
        email: document.getElementById("email").value,
        password: pw,
        confirm_password: cpw,
      });
      showAlert(alert, "Account created successfully. Redirecting to login…", "success");
      setTimeout(() => (window.location.href = "login.html"), 1400);
    } catch (err) {
      showAlert(alert, err.message, "error");
      btn.disabled = false;
    }
  });
}

/* ---- Profile setup screen ------------------------------------------------ */
function wireProfile() {
  const form = document.getElementById("profileForm");
  if (!form) return;
  const alert = document.getElementById("alert");
  const btn = document.getElementById("submitBtn");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAlert(alert);
    btn.disabled = true;
    try {
      await api("/api/profile", {
        first_name: document.getElementById("first_name").value,
        last_name: document.getElementById("last_name").value,
        phone: document.getElementById("phone").value,
        address: document.getElementById("address").value,
        city: document.getElementById("city").value,
        province: document.getElementById("province").value,
      });
      window.location.href = "dashboard.html";
    } catch (err) {
      showAlert(alert, err.message, "error");
      btn.disabled = false;
    }
  });
}

/* ---- Dashboard: greet the logged-in user, guard the route ---------------- */
async function wireDashboard() {
  const greeting = document.getElementById("greeting");
  if (!greeting) return;
  try {
    const res = await fetch("/api/me");
    const data = await res.json();
    if (!data.logged_in) { window.location.href = "login.html"; return; }
    const name = data.first_name || data.email.split("@")[0];
    greeting.textContent = `Welcome aboard, ${name}.`;
    const emailEl = document.getElementById("navEmail");
    if (emailEl) emailEl.textContent = data.email;
  } catch (_) { /* leave page as-is on transient error */ }
}

async function logout() {
  await fetch("/api/logout", { method: "POST" });
  window.location.href = "login.html";
}

document.addEventListener("DOMContentLoaded", () => {
  wireLogin();
  wireSignup();
  wireProfile();
  wireDashboard();
  wireBookings();
});
