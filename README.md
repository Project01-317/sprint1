# Group 15 — Airline Flight Reservation System

CP317-F course project. This repository delivers user accounts, flight search,
the real booking/cancel spine, role-based access control, and the ADM-02
passenger-list seat map. Built with **FastAPI + SQLite + SQLAlchemy** on the
backend and **vanilla HTML/CSS/JS** on the frontend. Ships with both a
**light** and a **dark** theme.

---

## Team (Group 15)

| Role | Member |
|------|--------|
| Product Owner (Developer) | Aryan Shah |
| Scrum Master (Developer) | Shazaib Malik |
| Frontend Lead Developer | Noah Yamin |
| Backend Lead Developer | Abdullah Mumtaz |
| Database Engineer (Developer) | Mustafa Khan |
| UI/UX Designer (Developer) | Varun Saini |
| QA/Test Engineer (Developer) | Nowaisir Alam |
| DevOps Engineer (Developer) | Ojas Chindarkar |
| Full-Stack Developer | Qazi Zayad |

---

## Product backlog

| Story ID | Title | Points | Priority | Sprint |
|----------|-------|:------:|----------|--------|
| UI-01  | Search Flights        | 5 | High   | Sprint 1 |
| UI-02  | View Flight Details   | 5 | High   | Sprint 1 |
| RES-01 | Book Flight           | 3 | High   | Sprint 1 |
| RES-02 | Cancel Reservation    | 3 | Medium | Sprint 1 |
| ACC-01 | User Login            | 3 | High   | Sprint 1 |
| ACC-02 | View Booking History  | 5 | Medium | Sprint 2 |
| ADM-01 | Manage Flights        | 5 | High   | Sprint 2 |
| ADM-02 | View Passenger List   | 5 | High   | Sprint 2 |
| REP-01 | Generate Reports      | 8 | Medium | Sprint 3 |
| SEC-01 | Secure Payments       | 8 | High   | Sprint 3 |

---

## What this repo delivers

| Story | Title | Status |
|-------|-------|--------|
| ACC-01 | User Login | Done |
| UI-01 | Search Flights | Done |
| UI-02 | View Flight Details | Done |
| RES-01 | Book Flight | Done |
| RES-02 | Cancel Reservation | Done |
| ADM-02 | View Passenger List (seat map) | Done |
| — | RBAC (`role` on users + `require_admin`) | Done |

**ACC-01 — User Login.** Login → Sign Up → Profile Setup → Dashboard.
Passwords are Argon2id-hashed; sessions use signed cookies.

**UI-01 / UI-02 — Search & Details.** Real `flights` table (150 seeded rows).
`GET /api/flights/search`, `/airports`, and `/{id}`.

**RES-01 — Book Flight.** `POST /api/bookings` writes a real `reservations`
row for a logged-in user, validates the seat against the aircraft config,
rejects taken seats / full flights, generates a booking reference, and
decrements `seats_available`.

**RES-02 — Cancel Reservation.** Now backed by the `reservations` table (the
old in-memory dummy store is gone). Cancelling flips status to `CANCELLED`,
frees the seat back into inventory, and issues a verification code — the
existing cancel UI is unchanged.

**ADM-02 — View Passenger List.** Admin-only manifest plus a **visual seat
map** of the aircraft cabin (A320 single-aisle / B787 twin-aisle), driven by
`backend/aircraft.py`. Occupied seats reveal passenger + booking reference to
admins only; a table-view toggle provides an accessible fallback. Reached from
`passengers.html` (a nav link appears on the dashboard for admin accounts).

**RBAC.** Users carry a `role` (`customer` | `admin`). Admin endpoints depend
on `require_admin`, so standard users get `403`. The seat-map endpoint omits
passenger identities for non-admins (privacy).

### Key API endpoints

| Method + path | Auth | Purpose |
|---------------|------|---------|
| `POST /api/bookings` | login | Book a flight (RES-01) |
| `GET /api/bookings[/ongoing\|/cancelled]` | login | List your reservations |
| `PUT /api/bookings/{id}/cancel` | login | Cancel a reservation (RES-02) |
| `GET /api/flights/{id}/passengers` | **admin** | Manifest (ADM-02) |
| `GET /api/flights/{id}/seatmap` | login | Seat map (names admin-only) |

---

## Setup

Requires Python 3.10+.

```bash
# 1. From the project root, create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Seed the database (flights first, then reservations + accounts)
python seed_flights.py         # 150 flights with A320/B787 aircraft types
python seed_reservations.py    # admin + sample customers + reservations

# 4. Run the app (serves API + frontend together)
uvicorn backend.main:app --reload
```

Then open **http://127.0.0.1:8000** in your browser.

> **Schema change / clean checkout:** this sprint adds columns (`users.role`,
> `flights.aircraft_type`) and the `reservations` table. `create_all` does not
> alter existing tables, so if you have an **old `airline.db`**, delete it and
> reseed: `rm airline.db && python seed_flights.py && python seed_reservations.py`.
> `seed_flights.py` now creates the tables itself, so it no longer crashes on a
> fresh checkout.

---

## Test credentials

Seeded by `seed_reservations.py`:

| Role | Email | Password |
|------|-------|----------|
| Admin (ADM-02) | `admin@air.ca` | `admin1234` |
| Customer | `aisha@air.ca` (and marco/wei/sara/liam @air.ca) | `skyhigh12` |

Or create your own account through the Sign Up screen (new accounts are
`customer` by default).

---

## How the login flow works

1. **Sign Up** validates the email format, password length (min 8), and that
   the two passwords match, then stores the account.
2. Passwords are **hashed with Argon2id** before storage — the plaintext is
   never saved. (See `backend/auth.py`.)
3. **Login** verifies the entered password against the stored hash. On success
   it checks whether a profile exists: if not, it routes to **Profile Setup**;
   if so, straight to the **Dashboard**.
4. Sessions use signed cookies, so the browser never holds a raw user id.

---

## Running the tests

```bash
pip install pytest httpx
pytest -v
```

`tests/test_auth.py` covers the ACC-01 login flow (registration, duplicate
emails, password validation, login routing, Argon2id hashing).
`tests/test_bookings.py` covers the reservations spine against a throwaway DB:
booking (create, invalid seat → 400, seat-taken → 409, full flight → 409),
cancel (verification code, seat freeing, wrong-email → 403, double-cancel → 400,
ownership), RBAC (customer → 403 / admin → 200), and the ADM-02 manifest +
seat-map privacy (names hidden for customers, revealed for admins).

---

## Taking screenshots for the Sprint 1 PDF

1. Run the app and open each screen: `login.html`, `signup.html`,
   `profile.html`, `dashboard.html`, and (as admin) `passengers.html`.
2. Use the floating **theme toggle** (top-right) to capture each in both light
   and dark.
3. For the "database connection" evidence, run:
   ```bash
   sqlite3 airline.db "SELECT id, email, substr(password_hash,1,30) FROM users;"
   ```
   and screenshot the hashed-password output — it shows the DB is real and that
   passwords are not stored in plaintext.

---

## Project structure

```
group15-airline/
├── backend/
│   ├── main.py          # FastAPI routes + static serving
│   ├── database.py      # SQLAlchemy engine + User/UserProfile/Flight/Reservation
│   ├── aircraft.py      # A320/B787 cabin configs + seat helpers (seat map)
│   ├── auth.py          # Argon2id hashing helpers
│   └── requirements.txt
├── frontend/
│   ├── login.html  signup.html  profile.html  dashboard.html  passengers.html
│   ├── css/styles.css   # both themes via CSS variables (+ seat-map styles)
│   └── js/app.js
├── seed_flights.py      # seed 150 flights (run first)
├── seed_reservations.py # seed admin + customers + reservations (run second)
├── tests/test_auth.py   tests/test_bookings.py
└── README.md
```
