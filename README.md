# Group 15 — Airline Flight Reservation System

CP317-F course project. This repository currently delivers two Sprint 1
modules — **ACC-01: User Login** and **RES-02: Cancel Reservation**. Built with
**FastAPI + SQLite + SQLAlchemy** on the backend and **vanilla HTML/CSS/JS** on
the frontend. Ships with both a **light** and a **dark** theme.

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
| RES-02 | Cancel Reservation | Done |

**ACC-01 — User Login**
> *As a user, I want to securely log into my account using my email and password
> so that I can manage my bookings.*

Screens: **Login → Sign Up → Profile Setup → Dashboard**.

**RES-02 — Cancel Reservation**
> *As a user, I want to cancel my reservation through my account so that I can
> change my travel plans without needing to contact support.*

From the dashboard, **My Bookings** lists ongoing and cancelled reservations.
Cancelling prompts the user to re-confirm their account email, then issues a
**verification code** and records a cancellation timestamp under *Cancelled
Bookings*.

The dashboard also stubs the remaining Sprint 1 stories — Search Flights, View
Flight Details, Book Flight — so the rest of the team has a place to plug in.

> **Note:** RES-02 booking records are currently in-memory demo data seeded per
> user (see `dummy_booking_templates` in `backend/main.py`), not yet persisted
> to the SQLite database.

---

## Setup

Requires Python 3.10+.

```bash
# 1. From the project root, create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Run the app (serves API + frontend together)
uvicorn backend.main:app --reload
```

Then open **http://127.0.0.1:8000** in your browser. The SQLite database
(`airline.db`) is created automatically on first run.

---

## Test credentials

There are none pre-seeded — create an account through the Sign Up screen. For a
quick demo:

- Email: `test@laurier.ca`
- Password: `airline2026`

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

Ten tests cover the ACC-01 login flow: registration, duplicate emails, password
mismatch, login success/failure, the profile-then-dashboard routing, and a check
that the stored password is an Argon2id hash rather than plaintext. (RES-02
cancellation is not yet covered by automated tests.)

---

## Taking screenshots for the Sprint 1 PDF

1. Run the app and open each screen: `login.html`, `signup.html`,
   `profile.html`, `dashboard.html`.
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
group15-airline-auth/
├── backend/
│   ├── main.py          # FastAPI routes + static serving
│   ├── database.py      # SQLAlchemy engine + User / UserProfile models
│   ├── auth.py          # Argon2id hashing helpers
│   └── requirements.txt
├── frontend/
│   ├── login.html  signup.html  profile.html  dashboard.html
│   ├── css/styles.css   # both themes via CSS variables
│   └── js/app.js
├── tests/test_auth.py
└── README.md
```
