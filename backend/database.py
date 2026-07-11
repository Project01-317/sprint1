"""
database.py
-----------
SQLAlchemy setup for the ACC-01 (User Login) module of the Group 15
Airline Flight Reservation System.

We keep authentication data (users) separate from personal data
(user_profiles). This is intentional: the password hash lives in one
table, and personally identifiable information (name, address, phone)
lives in another, linked by user_id. Separating them keeps the login
path from ever touching profile data and makes the schema easy to extend
for later sprints (bookings, payments).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Float, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# SQLite file lives at the project root. check_same_thread=False lets
# FastAPI's threadpool share the connection safely for this prototype.
DATABASE_URL = "sqlite:///./airline.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    """Authentication record. One row per account."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # We store ONLY the Argon2id hash here, never the plaintext password.
    password_hash = Column(String, nullable=False)
    # Role-based access control. "customer" (default) or "admin". Admin-only
    # endpoints (e.g. ADM-02 View Passenger List) are gated on this.
    role = Column(String, nullable=False, default="customer")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # One-to-one link to the profile (created during Profile Setup).
    profile = relationship(
        "UserProfile", back_populates="user", uselist=False,
        cascade="all, delete-orphan"
    )


class UserProfile(Base):
    """Personal details entered on the Profile Setup screen."""
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    address = Column(String, nullable=False)
    city = Column(String, nullable=False)
    province = Column(String, nullable=False)

    user = relationship("User", back_populates="profile")


class Flight(Base):
    """Flight schedules and inventory."""
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, index=True)
    flight_number = Column(String, unique=True, index=True, nullable=False)
    airline = Column(String, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_time = Column(DateTime, nullable=False)
    arrival_time = Column(DateTime, nullable=False)
    price = Column(Float, nullable=False)
    seats_available = Column(Integer, nullable=False)
    # Aircraft model (e.g. "A320", "B787"). Drives the seat-map layout so the
    # UI can render the correct cabin. Defaults to A320 if a seed omits it.
    aircraft_type = Column(String, nullable=False, default="A320")


class Reservation(Base):
    """
    A booking that links a passenger (user) to a real flight.

    This is the shared spine for the reservation stories: RES-01 (Book) creates
    a row here, RES-02 (Cancel) flips its status, ACC-02 (Booking History) lists
    a user's rows, and ADM-02 (View Passenger List) queries rows by flight_id
    joined to user_profiles to build a manifest.
    """
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    flight_id = Column(Integer, ForeignKey("flights.id"), nullable=False, index=True)
    # Human-readable confirmation code shown to the user (e.g. "ABCD12").
    booking_reference = Column(String, unique=True, index=True, nullable=False)
    # Assigned seat (e.g. "12A"). Nullable until the seat-selection story lands.
    seat = Column(String, nullable=True)
    # "CONFIRMED" (default) or "CANCELLED" — same vocabulary RES-02 already uses.
    status = Column(String, nullable=False, default="CONFIRMED")
    # Optional manifest field (wheelchair, dietary, etc.) for ADM-02.
    special_accommodations = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    cancelled_at = Column(DateTime, nullable=True)

    # Unidirectional links so the passenger-list join is easy and we don't have
    # to modify the User/Flight classes.
    user = relationship("User")
    flight = relationship("Flight")


def init_db() -> None:
    """Create tables if they do not exist (runs on app startup)."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
