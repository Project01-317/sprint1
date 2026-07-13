# Group 15 — Airline Flight Reservation System

CP317-F course project. A web-based airline reservation system: customers search
flights, view details, book a seat, cancel, and review their bookings; admins
manage flight schedules and view per-flight passenger manifests on a visual seat
map. Built with **FastAPI + SQLAlchemy + SQLite** on the backend and **vanilla
HTML/CSS/JS** on the frontend, with light and dark themes.

---

## Team (Group 15)

| Role | Member |
|------|--------|
| **Product Owner** (Developer) | **Aryan Shah** |
| Scrum Master (Developer) | Shazaib Malik |
| Frontend Lead Developer | Noah Yamin |
| Backend Lead Developer | Abdullah Mumtaz |
| Database Engineer (Developer) | Mustafa Khan |
| UI/UX Designer (Developer) | Varun Saini |
| QA/Test Engineer (Developer) | Nowaisir Alam |
| DevOps Engineer (Developer) | Ojas Chindarkar |
| Full-Stack Developer | Qazi Zayad |

---

## Story status

Legend: ✅ Done · 🟡 Partial · ⬜ Not started

| Story | Title | Sprint | Status | Notes |
|-------|-------|--------|:------:|-------|
| ACC-01 | User Login | 1 | ✅ | Register, login, profile setup; Argon2id hashing; session cookies (admins skip profile setup) |
| UI-01 | Search Flights | 1 | ✅ | Search by origin/destination/date against a real flights table |
| UI-02 | View Flight Details | 1 | ✅ | Full flight metadata endpoint + detail view |
| RES-01 | Book Flight | 1 | ✅ | Web flow: search → seat-map selection → confirmation with booking reference; persists a reservation, decrements seats |
| RES-02 | Cancel Reservation | 1 | ✅ | Runs on the real reservations table; email-confirmation guard; frees the seat |
| ADM-01 | Manage Flights | 2 | ✅ | Admin CRUD on flights, with capacity validation |
| ADM-02 | View Passenger List | 2 | ✅ | Visual seat map + manifest; admin-only; passenger identity hidden from customers |
| ACC-02 | View Booking History | 2 | ✅ | "My Bookings" split into Upcoming / Past / Cancelled (server-side); booking reference shown; downloadable PDF e-ticket per confirmed booking |
| REP-01 | Generate Reports | 3 | ⬜ | Not started (route popularity / booking trends) |
| SEC-01 | Secure Payments | 3 | ⬜ | Not started (payment gateway integration) |

**Summary: 8 stories complete, 2 not started.** Remaining work is Sprint 3
scope — reporting/analytics (REP-01) and payments (SEC-01).

---

## Features delivered

- **Accounts & profiles** — registration, login, profile setup; passwords hashed
  with **Argon2id**; server-side sessions. Admin accounts skip the customer
  profile-setup step and land on the dashboard.
- **Role-based access control** — `users.role` (`customer` / `admin`); a
  `require_admin` guard protects all admin endpoints (verified: customers get
  `403`).
- **Flight search & details** — real `flights` table (seeded), searchable by
  origin/destination/date, plus a full detail endpoint.
- **Booking** — end-to-end web flow: pick a flight, choose a seat on the visual
  seat map, optionally add accommodations, then confirm. Persists a `reservation`
  linked to a real flight, generates a `booking_reference`, decrements
  `seats_available`, and shows a confirmation screen; the reservation then
  appears under "My Bookings".
- **Cancellation** — on the real reservations table; requires email confirmation;
  flips status to `CANCELLED`, frees the seat, returns a verification code.
- **Booking history (ACC-02)** — "My Bookings" is split server-side into
  **Upcoming / Past / Cancelled** (by the flight's departure time); each card
  shows the booking reference and a **Download E-Ticket** button that returns a
  boarding-pass style **PDF** (reportlab) with route, times, seat, class,
  booking reference, and a barcode. Ownership-guarded (404 for others' tickets).
- **Admin — Manage Flights (ADM-01)** — create/update/delete flights with
  capacity validation against confirmed reservations.
- **Admin — Passenger List (ADM-02)** — per-flight manifest rendered as a
  **visual aircraft seat map** styled like an airline fleet map: a fuselage with
  colour-coded seat types (Standard / Preferred / Extra legroom / Business),
  over-wing exit rows, and centred cabins (A320 3-3 single-aisle, B787 3-3-3
  twin-aisle). Occupied seats reveal the passenger + booking reference + any
  accommodation to admins only; a table view provides an accessible fallback.

### Accessibility

The project targets WCAG-style accessibility:

- Seats are real focusable `<button>`s with descriptive `aria-label`s
  (e.g. "Seat 14C, Extra legroom, occupied, Aisha Khan").
- State is never conveyed by colour alone — occupied/selected differ in fill and
  are described in the label; an accommodation marker (♿) supplements colour.
- The passenger manifest has a **table view toggle** as a screen-reader- and
  keyboard-friendly alternative to the visual map.
- Light and dark themes with a persisted toggle.

---

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite, Argon2 (`argon2-cffi`),
  reportlab (PDF e-tickets)
- **Frontend:** vanilla HTML / CSS / JavaScript (served as static files)
- **Tests:** pytest + FastAPI `TestClient`

---

## Project structure

```
Airline_sprint1/
├── backend/
│   ├── main.py              # all API routes
│   ├── database.py          # SQLAlchemy models: User, UserProfile, Flight, Reservation
│   ├── aircraft.py          # A320 / B787 cabin layouts + seat-type/exit-row config
│   ├── auth.py              # Argon2id hashing
│   └── requirements.txt
├── frontend/
│   ├── login.html  signup.html  profile.html
│   ├── dashboard.html       # search, booking flow, My Bookings
│   ├── manage-flights.html  # ADM-01 admin CRUD UI
│   ├── passengers.html      # ADM-02 seat-map / passenger list
│   ├── css/styles.css
│   └── js/app.js            # app logic + shared seat-map component
│       js/manage-flights.js
├── seed_flights.py          # seeds ~150 flights (self-creates tables)
├── seed_reservations.py     # seeds an admin, customers, and sample reservations
├── tests/                   # test_auth.py, test_bookings.py, test_manage_flights.py
├── BookFlightsUI.py         # obsolete standalone Tkinter prototype — kept for reference, NOT part of the web app
├── .env.example             # SESSION_SECRET_KEY template
└── README.md
```

---

## Setup & run

Requires **Python 3.10+**.

```bash
pip install -r backend/requirements.txt

# Seed data — run flights first, then reservations (reservations attach to real
# flights, so they need the flights to exist):
python3 seed_flights.py         # ~150 flights across A320 and B787 aircraft
python3 seed_reservations.py    # admin + customer accounts + sample reservations

# Run the app:
uvicorn backend.main:app --reload
```

Open **http://localhost:8000** (redirects to the login page). The SQLite
database file `airline.db` is created automatically.

### Test credentials (from `seed_reservations.py`)

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@air.ca` | `admin1234` |
| Customer | `aisha@air.ca` | `skyhigh12` |

(Additional seeded customers use the same customer password.)

---

## API reference

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/register` | — | Create an account |
| POST | `/api/login` | — | Authenticate; returns `role` + `next_screen` |
| POST | `/api/profile` | session | Save passenger profile |
| GET | `/api/me` | — | Current session / role / profile status |
| POST | `/api/logout` | session | End session |
| POST | `/api/bookings` | session | Book a flight (seat + reservation) |
| GET | `/api/bookings` `/ongoing` `/upcoming` `/past` `/cancelled` | session | Current user's reservations (ACC-02 history split) |
| PUT | `/api/bookings/{id}/cancel` | session | Cancel a reservation |
| GET | `/api/bookings/{id}/ticket` | session | Download a PDF e-ticket (owner only) |
| GET | `/api/flights/airports` | — | Distinct origins/destinations |
| GET | `/api/flights/search` | — | Search flights |
| GET | `/api/flights/{id}` | — | Flight details |
| GET | `/api/flights/{id}/seatmap` | session | Seat map + occupancy + seat types (names admin-only) |
| GET | `/api/flights/{id}/passengers` | **admin** | Passenger manifest (ADM-02) |
| GET/POST/PUT/DELETE | `/api/admin/flights` | **admin** | Manage flights (ADM-01) |

---

## Tests

```bash
pip install pytest
pytest -q
```

**Current status: 49 tests passing** — `test_auth.py` (10, login/registration),
`test_bookings.py` (23, booking + cancel + RBAC + seat-map/manifest + ACC-02
history & e-ticket), `test_manage_flights.py` (16, admin CRUD + RBAC).

---

## Known issues & limitations

- **REP-01 (reports) and SEC-01 (payments) are not started** — planned for
  Sprint 3.
- **No real payment step** — booking completes without payment; SEC-01 will add
  the gateway.
- **Seat-map layouts are simplified** — the A320 and B787 configs in
  `aircraft.py` (cabins, seat types, exit rows) are representative, not exact
  airline cabins.
- **`BookFlightsUI.py` is obsolete** — an early standalone Tkinter prototype with
  hardcoded flights and no persistence. It is kept in the repo for reference but
  is not part of the web app; the real booking path is the web flow via
  `POST /api/bookings`.
- **Schema note for contributors:** the database is created via
  `Base.metadata.create_all`, which does not migrate an existing `airline.db`. If
  you pull schema changes, delete `airline.db` and reseed.
