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

    // Admin navigation is rendered only after the role has been checked.
    if (data.role === "admin") {
      ensureAdminNavigation("dashboard");
    }
  } catch (_) { /* leave page as-is on transient error */ }
}

async function logout() {
  await fetch("/api/logout", { method: "POST" });
  window.location.href = "login.html";
}

function ensureAdminNavigation(activePage) {
  const spacer = document.querySelector(".app-nav .spacer");
  if (!spacer) return;
  const entries = [
    ["passengerListNav", "passengers.html", "Passenger List", "passengers"],
    ["manageFlightsNav", "manage-flights.html", "Flights", "flights"],
  ];
  entries.forEach(([id, href, label, page]) => {
    let link = document.getElementById(id);
    if (!link) {
      link = document.createElement("a");
      link.id = id;
      link.href = href;
      link.textContent = label;
      spacer.parentNode.insertBefore(link, spacer);
    }
    link.classList.toggle("active", activePage === page);
  });
}

/* ---- Flight Search / Live Filter View ------------------------------------ */
function wireFlightSearch() {
  const searchNav = document.getElementById("searchFlightsNav");
  const searchSection = document.getElementById("searchSection");
  const form = document.getElementById("flightSearchForm");
  const resultsContainer = document.getElementById("searchResults");
  const searchAlert = document.getElementById("searchAlert");
  const bookingsSection = document.getElementById("bookingsSection");
  const airportDatalist = document.getElementById("airportOptions");

  if (!searchSection || !form) return;

  // Master function to execute search queries and render cards
  async function fetchAndRenderFlights(origin = "", dest = "", date = "") {
    clearAlert(searchAlert);
    resultsContainer.innerHTML = '<div class="empty-state" style="text-align:center;">Analyzing route updates...</div>';

    try {
      const params = new URLSearchParams();
      if (origin) params.append("origin", origin);
      if (dest) params.append("destination", dest);
      if (date) params.append("date", date);

      const res = await fetch(`/api/flights/search?${params.toString()}`);
      const flights = await res.json();

      if (!res.ok) throw new Error(flights.detail || "Could not complete flight lookup.");

      resultsContainer.innerHTML = "";
      
      if (flights.length === 0) {
        showAlert(searchAlert, "No scheduled paths match your chosen parameters.", "error");
        return;
      }

      flights.forEach(flight => {
        const card = document.createElement("div");
        card.className = "flight-card";
        
        const depDate = new Date(flight.departure_time);
        const timeStr = depDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const dateStr = depDate.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });

        card.innerHTML = `
          <div class="flight-info">
            <h4>${flight.airline} · <span style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--steel);">${flight.flight_number}</span></h4>
            <p class="flight-route"><strong>${flight.origin}</strong> to <strong>${flight.destination}</strong></p>
            <div class="flight-meta">
              <span>📅 ${dateStr}</span>
              <span>🕒 Departs: ${timeStr}</span>
              <span>⏳ ${flight.duration}</span>
              <span>💺 ${flight.seats} Seats left</span>
            </div>
          </div>
          <div class="flight-action">
            <span class="flight-price">$${flight.price.toFixed(2)}</span>
            <button class="btn btn-primary btn-small" onclick="selectFlight(${flight.id})">Select</button>
          </div>
        `;
        resultsContainer.appendChild(card);
      });
    } catch (err) {
      resultsContainer.innerHTML = "";
      showAlert(searchAlert, err.message, "error");
    }
  }

  // Populate drop-down autocompletes using distinct values found dynamically in the DB
  async function syncDropdownAutocompletes() {
    try {
      const res = await fetch("/api/flights/airports");
      if (res.ok) {
        const airports = await res.json();
        airportDatalist.innerHTML = "";
        airports.forEach(airport => {
          const option = document.createElement("option");
          option.value = airport;
          airportDatalist.appendChild(option);
        });
      }
    } catch (err) {
      console.error("Autofill metadata tracking failed:", err);
    }
  }

  // Handle nav tab interactions
  searchNav.addEventListener("click", (e) => {
    e.preventDefault();
    bookingsSection.hidden = true;
    searchSection.hidden = false;
    
    // Synchronize auto-suggestions and load a standard complete list first
    syncDropdownAutocompletes();
    fetchAndRenderFlights();
    
    searchSection.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  // Handle filter/search submissions
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const origin = document.getElementById("searchOrigin").value;
    const dest = document.getElementById("searchDest").value;
    const date = document.getElementById("searchDate").value;
    
    await fetchAndRenderFlights(origin, dest, date);
  });
}

/* ---- Flight Details / UI-02 ---------------------------------------------- */
async function selectFlight(flightId) {
  const modal = document.getElementById("flightDetailsModal");
  const content = document.getElementById("flightDetailsContent");
  const alert = document.getElementById("flightDetailsAlert");
  
  content.innerHTML = "Loading flight details...";
  clearAlert(alert);
  modal.hidden = false;

  try {
    const flight = await api(`/api/flights/${flightId}`, undefined, "GET");
    
    const depDate = new Date(flight.departure_time);
    const arrDate = new Date(flight.arrival_time);
    
    content.innerHTML = `
      <div style="margin-bottom: 1.5rem;">
        <strong style="font-size: 1.2rem;">${flight.airline}</strong> 
        <span style="color: var(--steel); margin-left: 8px;">Flight ${flight.flight_number}</span>
      </div>
      <ul style="list-style: none; padding: 0; line-height: 2;">
        <li><strong>Route:</strong> ${flight.origin} ➔ ${flight.destination}</li>
        <li><strong>Departure:</strong> ${depDate.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</li>
        <li><strong>Arrival:</strong> ${arrDate.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</li>
        <li><strong>Total Duration:</strong> ${flight.duration}</li>
        <li><strong>Inventory:</strong> ${flight.seats} seats available</li>
        <li><strong>Current Price:</strong> $${flight.price.toFixed(2)} CAD</li>
      </ul>
    `;
    
    document.getElementById("bookFlightBtn").onclick = () => {
      showAlert(alert, "Booking functionality (RES-01) will be implemented in the next sprint.", "success");
    };

  } catch (err) {
    content.innerHTML = "";
    showAlert(alert, err.message, "error");
  }
}

function closeFlightDetailsModal() {
  const modal = document.getElementById("flightDetailsModal");
  if (modal) modal.hidden = true;
}

/* ---- ADM-02 / RES-01: reusable seat map --------------------------------- */
/*
 * Renders a /seatmap payload into `container`. Build once, parameterized:
 *   adminView  — reveal passenger identity on occupied seats (admin only).
 *   selectable — allow clicking an available seat (booking flow); calls
 *                onSelect(seatId) and tracks a single highlighted selection.
 */
function renderSeatMap(payload, container, { adminView = false, selectable = false, onSelect = null } = {}) {
  container.innerHTML = "";
  let selectedSeat = null;

  payload.cabins.forEach((cabin) => {
    const section = document.createElement("div");
    section.className = "cabin";

    const label = document.createElement("h3");
    label.className = "cabin-label";
    label.textContent = cabin.class;
    section.appendChild(label);

    cabin.rows.forEach((row) => {
      const rowEl = document.createElement("div");
      rowEl.className = "seat-row";

      const num = document.createElement("span");
      num.className = "row-number";
      num.textContent = row.row;
      rowEl.appendChild(num);

      cabin.columns.forEach((col) => {
        const seat = row.seats.find((s) => s.seat === `${row.row}${col}`);
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `seat-btn ${seat.status}`;
        btn.textContent = col;

        const occupied = seat.status === "occupied";
        let aria = `Seat ${seat.seat}, ${seat.status}`;

        if (occupied && adminView && seat.passenger) {
          aria += `, ${seat.passenger}`;
          const parts = [seat.passenger, `Ref ${seat.booking_reference || "-"}`];
          if (seat.special_accommodations) parts.push(`Accommodation: ${seat.special_accommodations}`);
          const tip = parts.join(" · ");
          btn.addEventListener("mouseenter", (e) => showSeatTooltip(e, seat));
          btn.addEventListener("mousemove", moveSeatTooltip);
          btn.addEventListener("mouseleave", hideSeatTooltip);
          btn.addEventListener("focus", (e) => showSeatTooltip(e, seat));
          btn.addEventListener("blur", hideSeatTooltip);
          if (seat.special_accommodations) {
            const badge = document.createElement("span");
            badge.className = "accom-badge";
            badge.textContent = "♿";
            btn.appendChild(badge);
            aria += ", requires accommodation";
          }
          btn.title = tip;
        }

        if (occupied) btn.disabled = true;

        if (selectable && !occupied) {
          btn.addEventListener("click", () => {
            container.querySelectorAll(".seat-btn.selected").forEach((b) => {
              b.classList.remove("selected");
              b.classList.add("available");
            });
            btn.classList.remove("available");
            btn.classList.add("selected");
            selectedSeat = seat.seat;
            if (onSelect) onSelect(seat.seat);
          });
        } else if (!occupied) {
          btn.disabled = true; // admin/manifest view: seats are not clickable
        }

        btn.setAttribute("aria-label", aria);
        rowEl.appendChild(btn);

        if (cabin.aisles_after.includes(col)) {
          const gap = document.createElement("span");
          gap.className = "aisle-gap";
          gap.setAttribute("aria-hidden", "true");
          rowEl.appendChild(gap);
        }
      });

      section.appendChild(rowEl);
    });

    container.appendChild(section);
  });
}

let _seatTooltipEl = null;
function showSeatTooltip(e, seat) {
  hideSeatTooltip();
  _seatTooltipEl = document.createElement("div");
  _seatTooltipEl.className = "seat-tooltip";
  _seatTooltipEl.innerHTML =
    `<div><strong>${seat.passenger}</strong></div>` +
    `<div class="ref">${seat.booking_reference || ""}</div>` +
    (seat.special_accommodations ? `<div>♿ ${seat.special_accommodations}</div>` : "");
  document.body.appendChild(_seatTooltipEl);
  moveSeatTooltip(e);
}
function moveSeatTooltip(e) {
  if (!_seatTooltipEl) return;
  _seatTooltipEl.style.left = `${e.clientX + 14}px`;
  _seatTooltipEl.style.top = `${e.clientY + 14}px`;
}
function hideSeatTooltip() {
  if (_seatTooltipEl) { _seatTooltipEl.remove(); _seatTooltipEl = null; }
}

/* ---- ADM-02: admin passenger-list page ---------------------------------- */
async function wirePassengerList() {
  const select = document.getElementById("paxFlightSelect");
  if (!select) return;

  const alert = document.getElementById("paxAlert");
  const form = document.getElementById("paxFlightForm");
  const section = document.getElementById("seatmapSection");

  // Route guard: this page is admin-only.
  try {
    const me = await (await fetch("/api/me")).json();
    if (!me.logged_in) { window.location.href = "login.html"; return; }
    const emailEl = document.getElementById("navEmail");
    if (emailEl) emailEl.textContent = me.email;
    if (me.role !== "admin") {
      showAlert(alert, "Admin access required. Redirecting to dashboard…", "error");
      setTimeout(() => (window.location.href = "dashboard.html"), 1500);
      return;
    }
    ensureAdminNavigation("passengers");
  } catch (_) { window.location.href = "login.html"; return; }

  // Populate the flight dropdown from the search endpoint.
  try {
    const flights = await (await fetch("/api/flights/search")).json();
    flights.forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f.id;
      opt.textContent = `${f.flight_number} · ${f.origin} → ${f.destination}`;
      select.appendChild(opt);
    });
  } catch (_) {
    showAlert(alert, "Could not load flights.", "error");
  }

  // View toggle (seat map vs. accessible table).
  const mapBtn = document.getElementById("mapViewBtn");
  const tableBtn = document.getElementById("tableViewBtn");
  const mapView = document.getElementById("seatmapView");
  const tableView = document.getElementById("tableView");
  function setView(mode) {
    const isMap = mode === "map";
    mapBtn.classList.toggle("active", isMap);
    tableBtn.classList.toggle("active", !isMap);
    mapBtn.setAttribute("aria-pressed", isMap ? "true" : "false");
    tableBtn.setAttribute("aria-pressed", !isMap ? "true" : "false");
    mapView.hidden = !isMap;
    tableView.hidden = isMap;
  }
  mapBtn.addEventListener("click", () => setView("map"));
  tableBtn.addEventListener("click", () => setView("table"));

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const flightId = select.value;
    if (!flightId) return;
    clearAlert(alert);
    try {
      const [seatmap, manifest] = await Promise.all([
        api(`/api/flights/${flightId}/seatmap`, undefined, "GET"),
        api(`/api/flights/${flightId}/passengers`, undefined, "GET"),
      ]);

      section.hidden = false;
      document.getElementById("seatmapTitle").textContent =
        `${manifest.flight.flight_number} — ${seatmap.display_name}`;
      document.getElementById("seatmapSubtitle").textContent =
        `${manifest.flight.origin} → ${manifest.flight.destination}`;

      const cap = manifest.flight.capacity;
      const filled = manifest.count;
      const load = cap ? Math.round((filled / cap) * 100) : 0;
      document.getElementById("seatmapSummary").innerHTML =
        `<span><strong>${filled}</strong> filled</span>` +
        `<span><strong>${cap}</strong> capacity</span>` +
        `<span><strong>${load}%</strong> load factor</span>`;

      renderSeatMap(seatmap, mapView, { adminView: true });
      renderManifestTable(manifest.passengers);
      setView("map");
      section.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      showAlert(alert, err.message, "error");
    }
  });
}

function renderManifestTable(passengers) {
  const body = document.getElementById("paxTableBody");
  body.innerHTML = "";
  if (!passengers.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 5;
    cell.className = "empty-state";
    cell.textContent = "No passengers booked on this flight yet.";
    row.appendChild(cell);
    body.appendChild(row);
    return;
  }
  passengers.forEach((p) => {
    const row = document.createElement("tr");
    const name = [p.first_name, p.last_name].filter(Boolean).join(" ") || p.email || "-";
    [p.booking_reference, name, p.seat, p.seat_class, p.special_accommodations].forEach((v) => {
      const td = document.createElement("td");
      td.textContent = v || "-";
      row.appendChild(td);
    });
    body.appendChild(row);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  wireLogin();
  wireSignup();
  wireProfile();
  wireDashboard();
  wireBookings();
  wireFlightSearch();
});
