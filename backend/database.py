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
