"""
main.py
-------
FastAPI application for ACC-01 (User Login) — Group 15 Airline Flight
Reservation System.

Run with:
    uvicorn backend.main:app --reload

It serves both the JSON API (/api/...) and the static frontend, so the
whole prototype starts with a single command.
"""

import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import cast, Date
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .auth import hash_password, verify_password
from .database import Flight, User, UserProfile, get_db, init_db

# Load variables from a local .env file (gitignored) into the environment.
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()          # create tables on startup
    yield

app = FastAPI(title="Group 15 Airline — Auth Module", lifespan=lifespan)


# Signed-cookie sessions. The browser only ever sees a tamper-proof signed
# token, never the raw user id. The signing secret is read from the
# SESSION_SECRET_KEY environment variable (see .env / .env.example); the
# fallback is for local development only and must not be used in production.
SESSION_SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "cp317-group15-dev-secret")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Minimum password length enforced on the server (never trust the browser).
MIN_PASSWORD_LEN = 8
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --------------------------------------------------------------------------
# Request/response models
# --------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileRequest(BaseModel):
    first_name: str
    last_name: str
    phone: str
    address: str
    city: str
    province: str


class CancelBookingRequest(BaseModel):
    account_email: str


dummy_booking_templates = [
    {
        "id": 1,
        "passenger_name": "Ahmed",
        "flight_number": "AC101",
        "origin": "Toronto",
        "destination": "New York",
        "departure_date": "2026-06-30",
        "status": "CONFIRMED",
        "cancellation_timestamp": None,
        "verification_code": None,
    },
    {
        "id": 2,
        "passenger_name": "Ahmed",
        "flight_number": "AC202",
        "origin": "Toronto",
        "destination": "London",
        "departure_date": "2026-07-05",
        "status": "CONFIRMED",
        "cancellation_timestamp": None,
        "verification_code": None,
    },
    {
        "id": 3,
        "passenger_name": "Ahmed",
        "flight_number": "EK303",
        "origin": "Toronto",
        "destination": "Dubai",
        "departure_date": "2026-07-15",
        "status": "CANCELLED",
        "cancellation_timestamp": "2026-06-20T14:30:00+00:00",
        "verification_code": "CANCEL-BOOKING-3",
    },
]

dummy_bookings_by_email = {}


def normalize_email(email: str) -> str:
    return email.strip().lower()


def current_user_email(request: Request, db: Session) -> str:
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(401, "Please log in first.")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        request.session.clear()
        raise HTTPException(401, "Please log in first.")

    return normalize_email(user.email)


def bookings_for_user(email: str):
    email = normalize_email(email)
    if email not in dummy_bookings_by_email:
        dummy_bookings_by_email[email] = [
            {**booking, "account_email": email}
            for booking in dummy_booking_templates
        ]
    return dummy_bookings_by_email[email]


def find_dummy_booking(bookings, booking_id: int):
    return next((booking for booking in bookings if booking["id"] == booking_id), None)


# --------------------------------------------------------------------------
# Lifecycle handled by the lifespan context manager above.
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# API routes
# --------------------------------------------------------------------------
@app.post("/api/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    email = req.email.strip().lower()

    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Enter a valid email address.")
    if len(req.password) < MIN_PASSWORD_LEN:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    if req.password != req.confirm_password:
        raise HTTPException(400, "The passwords entered do not match.")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with that email already exists.")

    user = User(email=email, password_hash=hash_password(req.password))
    db.add(user)
    db.commit()
    return {"message": "Account created successfully. You can now log in."}


@app.post("/api/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = req.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if user is None or not verify_password(req.password, user.password_hash):
        # Same message for both cases so we don't reveal which emails exist.
        raise HTTPException(401, "Invalid email or password. Please try again.")

    request.session["user_id"] = user.id
    has_profile = user.profile is not None
    # next_screen mirrors the example's "if userInfo == null -> Profile Setup".
    return {
        "message": "Login successful.",
        "has_profile": has_profile,
        "next_screen": "dashboard" if has_profile else "profile",
    }


@app.post("/api/profile")
def save_profile(req: ProfileRequest, request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(401, "Please log in first.")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(404, "Account not found.")

    for field in ("first_name", "last_name", "phone", "address", "city", "province"):
        if not getattr(req, field).strip():
            raise HTTPException(400, "All profile fields are required.")

    if user.profile is None:
        user.profile = UserProfile(user_id=user.id, **req.model_dump())
    else:
        for field, value in req.model_dump().items():
            setattr(user.profile, field, value)

    db.commit()
    return {"message": "Profile saved.", "next_screen": "dashboard"}


@app.get("/api/me")
def me(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id is None:
        return {"logged_in": False}

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        request.session.clear()
        return {"logged_in": False}

    return {
        "logged_in": True,
        "email": user.email,
        "has_profile": user.profile is not None,
        "first_name": user.profile.first_name if user.profile else None,
    }


@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out."}


@app.get("/api/bookings")
def get_bookings(request: Request, db: Session = Depends(get_db)):
    email = current_user_email(request, db)
    return bookings_for_user(email)


@app.get("/api/bookings/ongoing")
def get_ongoing_bookings(request: Request, db: Session = Depends(get_db)):
    email = current_user_email(request, db)
    return [booking for booking in bookings_for_user(email) if booking["status"] == "CONFIRMED"]


@app.get("/api/bookings/cancelled")
def get_cancelled_bookings(request: Request, db: Session = Depends(get_db)):
    email = current_user_email(request, db)
    return [booking for booking in bookings_for_user(email) if booking["status"] == "CANCELLED"]


@app.put("/api/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    req: CancelBookingRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    email = current_user_email(request, db)
    confirmation_email = normalize_email(req.account_email)
    booking = find_dummy_booking(bookings_for_user(email), booking_id)
    if booking is None:
        raise HTTPException(404, "Booking not found.")
    if booking["status"] == "CANCELLED":
        raise HTTPException(400, "This booking is already cancelled.")

    if confirmation_email != email:
        raise HTTPException(403, "Email confirmation does not match your logged-in email.")
    if normalize_email(booking["account_email"]) != email:
        raise HTTPException(403, "You can only cancel your own booking.")

    verification_code = f"CANCEL-BOOKING-{booking['id']}"
    booking["status"] = "CANCELLED"
    booking["cancellation_timestamp"] = datetime.now(timezone.utc).isoformat()
    booking["verification_code"] = verification_code

    return {
        "message": (
            f"Booking #{booking['id']} has been cancelled successfully. "
            f"Verification code: {verification_code}. "
            "A record has been saved under Cancelled Bookings."
        ),
        "booking": booking,
        "verification_code": verification_code,
    }


@app.get("/api/flights/airports")
def get_unique_airports(db: Session = Depends(get_db)):
    """Returns a unique list of all origins and destinations currently in the database for autocomplete."""
    origins = db.query(Flight.origin).distinct().all()
    destinations = db.query(Flight.destination).distinct().all()
    
    # Flatten the tuples into a single unique set of strings
    airport_set = set([o[0] for o in origins] + [d[0] for d in destinations])
    return sorted(list(airport_set))


@app.get("/api/flights/search")
def search_flights(origin: str = None, destination: str = None, date: str = None, db: Session = Depends(get_db)):
    """
    Returns a filtered list of flights. 
    If no parameters are provided, it defaults to returning all available flights.
    """
    query = db.query(Flight).filter(Flight.seats_available > 0)

    if origin:
        query = query.filter(Flight.origin.ilike(f"%{origin}%"))
    if destination:
        query = query.filter(Flight.destination.ilike(f"%{destination}%"))
    if date:
        try:
            search_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(cast(Flight.departure_time, Date) == search_date)
        except ValueError:
            raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD.")

    # Sort results chronologically by departure time
    flights = query.order_by(Flight.departure_time.asc()).all()

    results = []
    for f in flights:
        dur = f.arrival_time - f.departure_time
        hours = int(dur.total_seconds() // 3600)
        minutes = int((dur.total_seconds() % 3600) // 60)
        results.append({
            "id": f.id,
            "flight_number": f.flight_number,
            "airline": f.airline,
            "origin": f.origin,
            "destination": f.destination,
            "departure_time": f.departure_time.isoformat(),
            "arrival_time": f.arrival_time.isoformat(),
            "price": f.price,
            "duration": f"{hours}h {minutes}m",
            "seats": f.seats_available
        })
    return results

@app.get("/api/flights/{flight_id}")
def get_flight_details(flight_id: int, db: Session = Depends(get_db)):
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found.")
    
    dur = flight.arrival_time - flight.departure_time
    hours = int(dur.total_seconds() // 3600)
    minutes = int((dur.total_seconds() % 3600) // 60)
    
    return {
        "id": flight.id,
        "flight_number": flight.flight_number,
        "airline": flight.airline,
        "origin": flight.origin,
        "destination": flight.destination,
        "departure_time": flight.departure_time.isoformat(),
        "arrival_time": flight.arrival_time.isoformat(),
        "duration": f"{hours}h {minutes}m",
        "price": flight.price,
        "seats": flight.seats_available
    }


# --------------------------------------------------------------------------
# Frontend (served last so /api routes take priority)
# --------------------------------------------------------------------------
@app.get("/")
def root():
    return FileResponse(FRONTEND_DIR / "login.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")