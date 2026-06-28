# Group 15 — Airline Flight Reservation System

## ACC-01: User Login Module (Sprint 1)

A working login, registration, and profile-setup prototype for the CP317F
Airline Flight Reservation System. Built with **FastAPI + SQLite + SQLAlchemy**
on the backend and **vanilla HTML/CSS/JS** on the frontend. Ships with both a
**light** and a **dark** theme.

---

## What this module covers

| Story | Title | Status |
|-------|-------|--------|
| ACC-01 | User Login | Done |

Screens: **Login → Sign Up → Profile Setup → Dashboard** (dashboard is a shell
stub so the rest of the team's Sprint 1 stories — Search, Bookings — have a
place to plug in).

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
2. Passwords are **hashed with bcrypt** before storage — the plaintext is never
   saved. (See `backend/auth.py`.)
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

Ten tests cover registration, duplicate emails, password mismatch, login
success/failure, the profile-then-dashboard routing, and a check that the
stored password is a bcrypt hash rather than plaintext.

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
│   ├── auth.py          # bcrypt hashing helpers
│   └── requirements.txt
├── frontend/
│   ├── login.html  signup.html  profile.html  dashboard.html
│   ├── css/styles.css   # both themes via CSS variables
│   └── js/app.js
├── tests/test_auth.py
└── README.md
```
