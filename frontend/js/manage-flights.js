/* ADM-01 — protected flight administration UI. Depends on shared app.js helpers. */

const manageFlightsState = {
  adminEmail: "",
  flights: [],
  editingFlight: null,
  pendingAction: null,
  openMenu: null,
  lastFocused: null,
};

function formatFlightDate(value) {
  return new Date(value).toLocaleString([], {
    year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

function toLocalDateTime(value) {
  const date = new Date(value);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}

function closeFlightActions() {
  if (!manageFlightsState.openMenu) return;
  const { button, menu } = manageFlightsState.openMenu;
  menu.hidden = true;
  button.setAttribute("aria-expanded", "false");
  manageFlightsState.openMenu = null;
}

function filteredManagedFlights() {
  const search = document.getElementById("manageFlightsSearch").value.trim().toLowerCase();
  return search
    ? manageFlightsState.flights.filter((flight) => flight.flight_number.toLowerCase().includes(search))
    : manageFlightsState.flights;
}

function renderFlights(flights = manageFlightsState.flights) {
  const body = document.getElementById("manageFlightsTableBody");
  const loading = document.getElementById("manageFlightsLoading");
  const empty = document.getElementById("manageFlightsEmpty");
  const wrap = document.getElementById("manageFlightsTableWrap");
  body.innerHTML = "";
  loading.hidden = true;
  empty.hidden = flights.length !== 0;
  empty.textContent = manageFlightsState.flights.length && !flights.length
    ? "No flights match that flight number."
    : "No flights are currently scheduled.";
  wrap.hidden = flights.length === 0;

  flights.forEach((flight) => {
    const row = document.createElement("tr");
    const flightCell = document.createElement("td");
    const number = document.createElement("strong");
    number.textContent = flight.flight_number;
    const airline = document.createElement("div");
    airline.className = "manage-flights-muted";
    airline.textContent = flight.airline;
    flightCell.append(number, airline);
    row.appendChild(flightCell);

    [
      `${flight.origin} → ${flight.destination}`,
      formatFlightDate(flight.departure_time),
      formatFlightDate(flight.arrival_time),
      `$${Number(flight.price).toFixed(2)} CAD`,
      String(flight.seats_available),
      flight.aircraft_type,
    ].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.appendChild(cell);
    });

    const actionsCell = document.createElement("td");
    actionsCell.className = "flight-actions-cell";
    const actionWrap = document.createElement("div");
    actionWrap.className = "flight-actions";
    const actionButton = document.createElement("button");
    actionButton.type = "button";
    actionButton.className = "flight-actions-trigger";
    actionButton.setAttribute("aria-label", `Actions for flight ${flight.flight_number}`);
    actionButton.setAttribute("aria-haspopup", "menu");
    actionButton.setAttribute("aria-expanded", "false");
    actionButton.textContent = "⋮";
    const menu = document.createElement("div");
    menu.className = "flight-actions-menu";
    menu.setAttribute("role", "menu");
    menu.hidden = true;
    [["Edit Flight", () => openFlightForm(flight)], ["Delete Flight", () => openDeleteConfirmation(flight)]].forEach(([label, action]) => {
      const item = document.createElement("button");
      item.type = "button";
      item.setAttribute("role", "menuitem");
      item.textContent = label;
      item.addEventListener("click", () => { closeFlightActions(); action(); });
      menu.appendChild(item);
    });
    actionButton.addEventListener("click", (event) => {
      event.stopPropagation();
      const wasOpen = manageFlightsState.openMenu && manageFlightsState.openMenu.menu === menu;
      closeFlightActions();
      if (!wasOpen) {
        menu.hidden = false;
        actionButton.setAttribute("aria-expanded", "true");
        manageFlightsState.openMenu = { button: actionButton, menu };
      }
    });
    actionWrap.append(actionButton, menu);
    actionsCell.appendChild(actionWrap);
    row.appendChild(actionsCell);
    body.appendChild(row);
  });
}

async function loadManagedFlights() {
  const alert = document.getElementById("manageFlightsAlert");
  const loading = document.getElementById("manageFlightsLoading");
  loading.hidden = false;
  clearAlert(alert);
  try {
    manageFlightsState.flights = await api("/api/admin/flights", undefined, "GET");
    renderFlights(filteredManagedFlights());
  } catch (err) {
    loading.hidden = true;
    showAlert(alert, err.message, "error");
  }
}

function openFlightForm(flight = null) {
  closeFlightActions();
  manageFlightsState.editingFlight = flight;
  manageFlightsState.lastFocused = document.activeElement;
  const form = document.getElementById("flightForm");
  const title = document.getElementById("flightFormTitle");
  const submit = document.getElementById("submitFlightFormBtn");
  const alert = document.getElementById("flightFormAlert");
  form.reset();
  clearAlert(alert);
  title.textContent = flight ? `Edit Flight ${flight.flight_number}` : "Add New Flight";
  submit.textContent = flight ? "Save Changes" : "Add Flight";
  if (flight) {
    Object.entries(flight).forEach(([key, value]) => {
      const input = form.elements.namedItem(key);
      if (input) input.value = key.endsWith("_time") ? toLocalDateTime(value) : value;
    });
  }
  document.getElementById("flightFormModal").hidden = false;
  document.getElementById("flightNumber").focus();
}

function closeFlightForm() {
  document.getElementById("flightFormModal").hidden = true;
  manageFlightsState.editingFlight = null;
  if (manageFlightsState.lastFocused) manageFlightsState.lastFocused.focus();
}

function formPayload() {
  const form = document.getElementById("flightForm");
  const values = Object.fromEntries(new FormData(form).entries());
  return {
    ...values,
    flight_number: values.flight_number.trim(),
    airline: values.airline.trim(),
    origin: values.origin.trim(),
    destination: values.destination.trim(),
    price: Number(values.price),
    seats_available: Number(values.seats_available),
  };
}

function validateFlightForm(payload) {
  if (!payload.flight_number || !payload.airline || !payload.origin || !payload.destination) {
    return "All flight details are required.";
  }
  if (payload.origin.toLowerCase() === payload.destination.toLowerCase()) {
    return "Origin and destination must be different.";
  }
  if (new Date(payload.arrival_time) <= new Date(payload.departure_time)) {
    return "Arrival time must be later than departure time.";
  }
  if (!Number.isFinite(payload.price) || payload.price <= 0) return "Price must be greater than zero.";
  if (!Number.isInteger(payload.seats_available) || payload.seats_available < 0) {
    return "Available seats must be a whole number of zero or more.";
  }
  return "";
}

function openConfirmation(action, payload, flight = null) {
  manageFlightsState.pendingAction = { action, payload, flight };
  manageFlightsState.lastFocused = document.activeElement;
  const titles = { create: "Confirm new flight", update: "Confirm flight changes", delete: "Confirm flight deletion" };
  const summary = action === "create"
    ? `You are about to add flight ${payload.flight_number}. Re-enter your admin account email to confirm.`
    : action === "update"
      ? `You are about to save changes to flight ${flight.flight_number}. Re-enter your admin account email to confirm.`
      : `You are about to delete flight ${flight.flight_number}. This cannot be undone. Re-enter your admin account email to confirm.`;
  document.getElementById("adminConfirmTitle").textContent = titles[action];
  document.getElementById("adminConfirmSummary").textContent = summary;
  document.getElementById("adminConfirmEmail").value = "";
  clearAlert(document.getElementById("adminConfirmAlert"));
  document.getElementById("adminConfirmModal").hidden = false;
  document.getElementById("adminConfirmEmail").focus();
}

function closeConfirmation() {
  document.getElementById("adminConfirmModal").hidden = true;
  manageFlightsState.pendingAction = null;
  if (manageFlightsState.lastFocused) manageFlightsState.lastFocused.focus();
}

function openDeleteConfirmation(flight) {
  openConfirmation("delete", null, flight);
}

function showSuccess(message) {
  manageFlightsState.lastFocused = document.activeElement;
  document.getElementById("flightSuccessMessage").textContent = message;
  document.getElementById("flightSuccessModal").hidden = false;
  document.getElementById("closeFlightSuccessBtn").focus();
}

function closeSuccess() {
  document.getElementById("flightSuccessModal").hidden = true;
  if (manageFlightsState.lastFocused) manageFlightsState.lastFocused.focus();
}

async function submitConfirmedAction(event) {
  event.preventDefault();
  const pending = manageFlightsState.pendingAction;
  if (!pending) return;
  const email = document.getElementById("adminConfirmEmail").value.trim();
  const alert = document.getElementById("adminConfirmAlert");
  const confirm = document.getElementById("confirmAdminActionBtn");
  clearAlert(alert);
  if (email.toLowerCase() !== manageFlightsState.adminEmail.toLowerCase()) {
    showAlert(alert, "Enter the email for the currently logged-in admin account.", "error");
    return;
  }
  confirm.disabled = true;
  try {
    if (pending.action === "create") {
      await api("/api/admin/flights", { ...pending.payload, account_email: email });
    } else if (pending.action === "update") {
      await api(`/api/admin/flights/${pending.flight.id}`, { ...pending.payload, account_email: email }, "PUT");
    } else {
      await api(`/api/admin/flights/${pending.flight.id}`, { account_email: email }, "DELETE");
    }
    const message = {
      create: "Flight successfully added.",
      update: "Flight successfully updated.",
      delete: "Flight successfully deleted.",
    }[pending.action];
    document.getElementById("adminConfirmModal").hidden = true;
    manageFlightsState.pendingAction = null;
    document.getElementById("flightFormModal").hidden = true;
    manageFlightsState.editingFlight = null;
    await loadManagedFlights();
    showSuccess(message);
  } catch (err) {
    showAlert(alert, err.message, "error");
  } finally {
    confirm.disabled = false;
  }
}

function wireManageFlightsEvents() {
  document.getElementById("manageFlightsSearch").addEventListener("input", () => {
    renderFlights(filteredManagedFlights());
  });
  document.getElementById("addFlightBtn").addEventListener("click", () => openFlightForm());
  document.getElementById("cancelFlightFormBtn").addEventListener("click", closeFlightForm);
  document.getElementById("cancelAdminConfirmBtn").addEventListener("click", closeConfirmation);
  document.getElementById("closeFlightSuccessBtn").addEventListener("click", closeSuccess);
  document.getElementById("flightForm").addEventListener("submit", (event) => {
    event.preventDefault();
    const payload = formPayload();
    const error = validateFlightForm(payload);
    const alert = document.getElementById("flightFormAlert");
    clearAlert(alert);
    if (error) { showAlert(alert, error, "error"); return; }
    openConfirmation(manageFlightsState.editingFlight ? "update" : "create", payload, manageFlightsState.editingFlight);
  });
  document.getElementById("adminConfirmForm").addEventListener("submit", submitConfirmedAction);
  document.addEventListener("click", closeFlightActions);
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    closeFlightActions();
    if (!document.getElementById("flightSuccessModal").hidden) closeSuccess();
    else if (!document.getElementById("adminConfirmModal").hidden) closeConfirmation();
    else if (!document.getElementById("flightFormModal").hidden) closeFlightForm();
  });
}

async function wireManageFlights() {
  const page = document.getElementById("manageFlightsPage");
  if (!page) return;
  try {
    const response = await fetch("/api/me");
    const me = await response.json();
    if (!me.logged_in) { window.location.href = "login.html"; return; }
    if (me.role !== "admin") { window.location.href = "dashboard.html"; return; }
    manageFlightsState.adminEmail = me.email;
    document.getElementById("navEmail").textContent = me.email;
    ensureAdminNavigation("flights");
    page.hidden = false;
    wireManageFlightsEvents();
    await loadManagedFlights();
  } catch (_) {
    window.location.href = "login.html";
  }
}

document.addEventListener("DOMContentLoaded", wireManageFlights);

let trendsDataCache = [];

async function loadReports() {
  const revenueChart = document.getElementById("revenueChart");
  const trendsChart = document.getElementById("trendsChart");
  if (!revenueChart && !trendsChart) return;

  const revResponse = await fetch('/api/reports/revenue');
  const revData = await revResponse.json();
  if (revenueChart) {
    new Chart(revenueChart, {
      type: 'line',
      data: {
        labels: revData.map((row) => row.date),
        datasets: [{
          label: 'Daily Revenue ($)',
          data: revData.map((row) => row.revenue),
          borderColor: 'green',
          fill: false,
        }],
      },
    });
  }

  const trendsResponse = await fetch('/api/reports/trends');
  trendsDataCache = await trendsResponse.json();
  if (trendsChart) {
    new Chart(trendsChart, {
      type: 'bar',
      data: {
        labels: trendsDataCache.map((row) => row.destination),
        datasets: [{
          label: 'Total Bookings',
          data: trendsDataCache.map((row) => row.bookings),
          backgroundColor: 'blue',
        }],
      },
    });
  }
}

function exportToCSV() {
  if (trendsDataCache.length === 0) return;

  let csvContent = 'data:text/csv;charset=utf-8,Destination,Bookings\n';
  trendsDataCache.forEach((row) => {
    csvContent += `${row.destination},${row.bookings}\n`;
  });

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement('a');
  link.setAttribute('href', encodedUri);
  link.setAttribute('download', 'travel_trends.csv');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadReports();
  const exportCsvBtn = document.getElementById('exportCsvBtn');
  if (exportCsvBtn) exportCsvBtn.addEventListener('click', exportToCSV);
});
