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
import secrets
import string
import math
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import cast, Date
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from . import aircraft
from .auth import hash_password, verify_password
from .database import Flight, Reservation, User, UserProfile, get_db, init_db

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


class BookingRequest(BaseModel):
    flight_id: int
    seat: Optional[str] = None
    special_accommodations: Optional[str] = None


class AdminFlightRequest(BaseModel):
    """ADM-01 payload for creating or updating an existing Flight row."""
    flight_number: str
    airline: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    price: float
    seats_available: int
    aircraft_type: str
    account_email: str


class AdminFlightDeleteRequest(BaseModel):
    """DELETE bodies are supported by FastAPI and keep confirmation private."""
    account_email: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


def current_user(request: Request, db: Session) -> User:
    """Resolve the logged-in User from the session, or raise 401."""
    user_id = request.session.get("user_id")
    if user_id is None:
        raise HTTPException(401, "Please log in first.")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        request.session.clear()
        raise HTTPException(401, "Please log in first.")

    return user


def current_user_email(request: Request, db: Session) -> str:
    return normalize_email(current_user(request, db).email)


def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI dependency: only allow requests from an admin account."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(401, "Please log in first.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "admin":
        raise HTTPException(403, "Admin access required.")
    return user


def generate_booking_reference() -> str:
    """Six-char confirmation code from A–Z and 0–9 (e.g. 'ABCD12')."""
    return "".join(
        secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
    )


def reservation_to_booking(res: Reservation) -> dict:
    """
    Map a Reservation row (+ joined flight/user) to the JSON shape the existing
    cancel/booking UI already consumes. The storage changed; the contract did
    not — the frontend keeps reading id/status/verification_code as before.
    """
    flight = res.flight
    user = res.user
    profile = user.profile if user else None
    if profile:
        passenger_name = f"{profile.first_name} {profile.last_name}".strip()
    elif user:
        passenger_name = user.email.split("@")[0]
    else:
        passenger_name = "-"

    return {
        "id": res.id,
        "passenger_name": passenger_name,
        "flight_number": flight.flight_number if flight else "-",
        "origin": flight.origin if flight else "-",
        "destination": flight.destination if flight else "-",
        "departure_date": flight.departure_time.date().isoformat() if flight else None,
        "status": res.status,
        "cancellation_timestamp": res.cancelled_at.isoformat() if res.cancelled_at else None,
        "verification_code": f"CANCEL-BOOKING-{res.id}" if res.status == "CANCELLED" else None,
        "account_email": normalize_email(user.email) if user else None,
        "seat": res.seat,
        "seat_class": aircraft.seat_class(flight.aircraft_type, res.seat)
        if (flight and res.seat) else None,
        "booking_reference": res.booking_reference,
        "special_accommodations": res.special_accommodations,
    }


# --------------------------------------------------------------------------
# ADM-01: flight management helpers
# --------------------------------------------------------------------------
def flight_to_admin_payload(flight: Flight) -> dict:
    """Serialize the complete existing Flight model for the admin table."""
    return {
        "id": flight.id,
        "flight_number": flight.flight_number,
        "airline": flight.airline,
        "origin": flight.origin,
        "destination": flight.destination,
        "departure_time": flight.departure_time.isoformat(),
        "arrival_time": flight.arrival_time.isoformat(),
        "price": flight.price,
        "seats_available": flight.seats_available,
        "aircraft_type": flight.aircraft_type,
    }


def _validated_admin_flight_values(
    req: AdminFlightRequest,
    db: Session,
    current_flight_id: Optional[int] = None,
) -> dict:
    """Validate ADM-01 input without changing the Flight schema or inventory."""
    values = {
        "flight_number": req.flight_number.strip(),
        "airline": req.airline.strip(),
        "origin": req.origin.strip(),
        "destination": req.destination.strip(),
        "departure_time": req.departure_time,
        "arrival_time": req.arrival_time,
        "price": req.price,
        "seats_available": req.seats_available,
        "aircraft_type": req.aircraft_type.strip(),
    }

    for field in ("flight_number", "airline", "origin", "destination"):
        if not values[field]:
            raise HTTPException(400, f"{field.replace('_', ' ').title()} is required.")
    if values["origin"].casefold() == values["destination"].casefold():
        raise HTTPException(400, "Origin and destination must be different.")
    if values["arrival_time"] <= values["departure_time"]:
        raise HTTPException(400, "Arrival time must be later than departure time.")
    if not math.isfinite(values["price"]) or values["price"] <= 0:
        raise HTTPException(400, "Price must be greater than zero.")
    if values["seats_available"] < 0:
        raise HTTPException(400, "Available seats cannot be negative.")
    if values["aircraft_type"] not in aircraft.AIRCRAFT_CONFIGS:
        raise HTTPException(400, "Aircraft type is not supported.")

    duplicate = db.query(Flight).filter(
        func.lower(Flight.flight_number) == values["flight_number"].casefold()
    )
    if current_flight_id is not None:
        duplicate = duplicate.filter(Flight.id != current_flight_id)
    if duplicate.first() is not None:
        raise HTTPException(409, "A flight with that flight number already exists.")

    confirmed = (
        db.query(Reservation)
        .filter(
            Reservation.flight_id == current_flight_id,
            Reservation.status == "CONFIRMED",
        )
        .all()
        if current_flight_id is not None else []
    )
    capacity = len(aircraft.all_seats(values["aircraft_type"]))
    if values["seats_available"] > capacity - len(confirmed):
        raise HTTPException(
            400,
            "Available seats cannot exceed aircraft capacity after confirmed reservations.",
        )

    # Changing an aircraft must not invalidate an already assigned seat.
    available_seat_ids = set(aircraft.all_seats(values["aircraft_type"]))
    if any(res.seat and res.seat not in available_seat_ids for res in confirmed):
        raise HTTPException(
            400,
            "The selected aircraft cannot preserve the flight's confirmed seat assignments.",
        )
    return values


def _confirm_admin_email(account_email: str, admin: User) -> None:
    if normalize_email(account_email) != normalize_email(admin.email):
        raise HTTPException(403, "Email confirmation does not match your logged-in email.")


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
    # Admins manage flights/passengers and don't book travel, so they don't need
    # a passenger profile — send them straight to the dashboard. Customers still
    # complete Profile Setup first (mirrors "if userInfo == null -> Profile Setup").
    is_admin = user.role == "admin"
    next_screen = "dashboard" if (has_profile or is_admin) else "profile"
    return {
        "message": "Login successful.",
        "has_profile": has_profile,
        "role": user.role,
        "next_screen": next_screen,
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
        "role": user.role,
        "has_profile": user.profile is not None,
        "first_name": user.profile.first_name if user.profile else None,
    }


@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out."}


def _user_reservations(db: Session, user_id: int, status: Optional[str] = None):
    """All of a user's reservations (optionally filtered by status), newest first."""
    query = db.query(Reservation).filter(Reservation.user_id == user_id)
    if status is not None:
        query = query.filter(Reservation.status == status)
    return query.order_by(Reservation.created_at.desc()).all()


@app.post("/api/bookings")
def create_booking(
    req: BookingRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """RES-01: the real booking path. Writes a reservation for a real flight."""
    user = current_user(request, db)

    flight = db.query(Flight).filter(Flight.id == req.flight_id).first()
    if flight is None:
        raise HTTPException(404, "Flight not found.")
    if flight.seats_available <= 0:
        raise HTTPException(409, "Flight is full.")

    seat = req.seat.strip().upper() if req.seat else None
    if seat:
        if aircraft.seat_class(flight.aircraft_type, seat) is None:
            raise HTTPException(400, "That is not a valid seat for this aircraft.")
        taken = (
            db.query(Reservation)
            .filter(
                Reservation.flight_id == flight.id,
                Reservation.seat == seat,
                Reservation.status == "CONFIRMED",
            )
            .first()
        )
        if taken:
            raise HTTPException(409, "Seat already taken.")

    # Generate a unique booking reference, regenerating on the rare collision.
    reference = generate_booking_reference()
    while db.query(Reservation).filter(Reservation.booking_reference == reference).first():
        reference = generate_booking_reference()

    reservation = Reservation(
        user_id=user.id,
        flight_id=flight.id,
        booking_reference=reference,
        seat=seat,
        status="CONFIRMED",
        special_accommodations=(req.special_accommodations or None),
    )
    flight.seats_available -= 1
    db.add(reservation)
    db.commit()
    db.refresh(reservation)

    return JSONResponse(
        status_code=201,
        content={
            "message": (
                f"Booking confirmed. Your reference is {reference}."
                + (f" Seat {seat}." if seat else "")
            ),
            "booking_reference": reference,
            "booking": reservation_to_booking(reservation),
        },
    )


@app.get("/api/bookings")
def get_bookings(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    return [reservation_to_booking(r) for r in _user_reservations(db, user.id)]


@app.get("/api/bookings/ongoing")
def get_ongoing_bookings(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    return [reservation_to_booking(r) for r in _user_reservations(db, user.id, "CONFIRMED")]


@app.get("/api/bookings/cancelled")
def get_cancelled_bookings(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    return [reservation_to_booking(r) for r in _user_reservations(db, user.id, "CANCELLED")]


@app.put("/api/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: int,
    req: CancelBookingRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    email = normalize_email(user.email)
    confirmation_email = normalize_email(req.account_email)

    reservation = db.query(Reservation).filter(Reservation.id == booking_id).first()
    if reservation is None or reservation.user_id != user.id:
        raise HTTPException(404, "Booking not found.")
    if reservation.status == "CANCELLED":
        raise HTTPException(400, "This booking is already cancelled.")
    if confirmation_email != email:
        raise HTTPException(403, "Email confirmation does not match your logged-in email.")

    verification_code = f"CANCEL-BOOKING-{reservation.id}"
    reservation.status = "CANCELLED"
    reservation.cancelled_at = datetime.now(timezone.utc)
    # Free the seat back into the flight's inventory.
    if reservation.flight is not None:
        reservation.flight.seats_available += 1
    db.commit()
    db.refresh(reservation)

    return {
        "message": (
            f"Booking #{reservation.id} has been cancelled successfully. "
            f"Verification code: {verification_code}. "
            "A record has been saved under Cancelled Bookings."
        ),
        "booking": reservation_to_booking(reservation),
        "verification_code": verification_code,
    }


# --------------------------------------------------------------------------
# ADM-01: Manage Flights (all operations are independently admin-protected)
# --------------------------------------------------------------------------
@app.get("/api/admin/flights")
def admin_list_flights(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    flights = db.query(Flight).order_by(Flight.departure_time.asc()).all()
    return [flight_to_admin_payload(flight) for flight in flights]


@app.post("/api/admin/flights", status_code=201)
def admin_create_flight(
    req: AdminFlightRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _confirm_admin_email(req.account_email, admin)
    values = _validated_admin_flight_values(req, db)
    flight = Flight(**values)
    db.add(flight)
    db.commit()
    db.refresh(flight)
    return flight_to_admin_payload(flight)


@app.put("/api/admin/flights/{flight_id}")
def admin_update_flight(
    flight_id: int,
    req: AdminFlightRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _confirm_admin_email(req.account_email, admin)
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if flight is None:
        raise HTTPException(404, "Flight not found.")

    values = _validated_admin_flight_values(req, db, current_flight_id=flight_id)
    for field, value in values.items():
        setattr(flight, field, value)
    db.commit()
    db.refresh(flight)
    return flight_to_admin_payload(flight)


@app.delete("/api/admin/flights/{flight_id}")
def admin_delete_flight(
    flight_id: int,
    req: AdminFlightDeleteRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _confirm_admin_email(req.account_email, admin)
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if flight is None:
        raise HTTPException(404, "Flight not found.")
    if db.query(Reservation).filter(Reservation.flight_id == flight_id).first():
        raise HTTPException(409, "A flight with existing reservations cannot be deleted.")

    db.delete(flight)
    db.commit()
    return {"message": "Flight successfully deleted."}


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
            query = query.filter(func.date(Flight.departure_time) == search_date.isoformat())
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
# ADM-02: Passenger list + seat map
# --------------------------------------------------------------------------
def _confirmed_reservations(db: Session, flight_id: int):
    """Every CONFIRMED reservation on a flight, joined to user + profile."""
    return (
        db.query(Reservation)
        .filter(
            Reservation.flight_id == flight_id,
            Reservation.status == "CONFIRMED",
        )
        .all()
    )


@app.get("/api/flights/{flight_id}/passengers")
def get_passenger_list(
    flight_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """ADM-02: the manifest — one entry per CONFIRMED reservation. Admin only."""
    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if flight is None:
        raise HTTPException(404, "Flight not found.")

    reservations = _confirmed_reservations(db, flight_id)
    passengers = []
    for res in reservations:
        user = res.user
        profile = user.profile if user else None
        passengers.append({
            "first_name": profile.first_name if profile else None,
            "last_name": profile.last_name if profile else None,
            "email": user.email if user else None,
            "seat": res.seat,
            "seat_class": aircraft.seat_class(flight.aircraft_type, res.seat)
            if res.seat else None,
            "booking_reference": res.booking_reference,
            "special_accommodations": res.special_accommodations,
        })

    capacity = len(aircraft.all_seats(flight.aircraft_type))
    return {
        "flight": {
            "flight_number": flight.flight_number,
            "origin": flight.origin,
            "destination": flight.destination,
            "aircraft_type": flight.aircraft_type,
            "seats_available": flight.seats_available,
            "capacity": capacity,
        },
        "passengers": passengers,
        "count": len(passengers),
    }


@app.get("/api/flights/{flight_id}/seatmap")
def get_seatmap(flight_id: int, request: Request, db: Session = Depends(get_db)):
    """
    The aircraft layout plus per-seat occupancy so the frontend can render the
    cabin. Requires a logged-in session. Passenger identity is only included
    when the requester is an admin (privacy for the customer booking flow).
    """
    user = current_user(request, db)
    is_admin = user.role == "admin"

    flight = db.query(Flight).filter(Flight.id == flight_id).first()
    if flight is None:
        raise HTTPException(404, "Flight not found.")

    # Map each occupied seat to its CONFIRMED reservation.
    occupancy = {
        res.seat: res
        for res in _confirmed_reservations(db, flight_id)
        if res.seat
    }

    cfg = aircraft.AIRCRAFT_CONFIGS.get(flight.aircraft_type) \
        or aircraft.AIRCRAFT_CONFIGS["A320"]

    cabins = []
    for cabin in cfg["cabins"]:
        rows = []
        for row_num in cabin["rows"]:
            seats = []
            for col in cabin["columns"]:
                seat_id = f"{row_num}{col}"
                res = occupancy.get(seat_id)
                seat_obj = {
                    "seat": seat_id,
                    "status": "occupied" if res else "available",
                    "seat_type": aircraft.seat_type(flight.aircraft_type, seat_id),
                }
                if res and is_admin:
                    u = res.user
                    p = u.profile if u else None
                    name = (
                        f"{p.first_name} {p.last_name}".strip()
                        if p else (u.email if u else None)
                    )
                    seat_obj["passenger"] = name
                    seat_obj["booking_reference"] = res.booking_reference
                    seat_obj["special_accommodations"] = res.special_accommodations
                seats.append(seat_obj)
            rows.append({"row": row_num, "seats": seats})
        cabins.append({
            "class": cabin["class"],
            "aisles_after": cabin["aisles_after"],
            "columns": cabin["columns"],
            "exit_rows": cabin.get("exit_rows", []),
            "rows": rows,
        })

    return {
        "aircraft_type": flight.aircraft_type,
        "display_name": cfg["display_name"],
        "flight": {
            "flight_number": flight.flight_number,
            "origin": flight.origin,
            "destination": flight.destination,
            "capacity": len(aircraft.all_seats(flight.aircraft_type)),
            "occupied": len(occupancy),
        },
        "cabins": cabins,
    }


# --------------------------------------------------------------------------
# Frontend (served last so /api routes take priority)
# --------------------------------------------------------------------------
@app.get("/")
def root():
    return FileResponse(FRONTEND_DIR / "login.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
