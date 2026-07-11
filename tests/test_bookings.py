"""
test_bookings.py — automated tests for the reservations spine.

Covers RES-01 (booking), RES-02 (cancel), RBAC, and ADM-02 (passenger list).
Run with:  pytest -v

Notes
-----
These tests were originally written against an in-memory dummy store. They now
seed real rows in a throwaway `reservations` table (same DB-swap pattern as
test_auth). The fixture drops + recreates all tables before every test so each
case is isolated.
"""

import os
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

# Use a throwaway database for tests, not the dev one (same pattern as test_auth).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import backend.database as database  # noqa: E402

TEST_DB = "sqlite:///./test_airline.db"
database.engine = database.create_engine(
    TEST_DB, connect_args={"check_same_thread": False}
)
database.SessionLocal.configure(bind=database.engine)

from backend import aircraft  # noqa: E402
from backend.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_state():
    """Reset the database before each test."""
    database.Base.metadata.drop_all(bind=database.engine)
    database.Base.metadata.create_all(bind=database.engine)
    yield


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def login_client(email="traveller@example.com", password="skyhigh12"):
    """Register + log in, returning a TestClient that holds the session cookie."""
    c = TestClient(app)
    c.post("/api/register", json={
        "email": email, "password": password, "confirm_password": password})
    c.post("/api/login", json={"email": email, "password": password})
    return c


def promote_to_admin(email):
    db = database.SessionLocal()
    user = db.query(database.User).filter(database.User.email == email).first()
    user.role = "admin"
    db.commit()
    db.close()


def seed_flight(flight_number="AC888", aircraft_type="A320", seats=None,
                origin="Toronto", destination="London"):
    """Insert a real flight and return its id."""
    db = database.SessionLocal()
    if seats is None:
        seats = len(aircraft.all_seats(aircraft_type))
    flight = database.Flight(
        flight_number=flight_number, airline="Air Canada",
        origin=origin, destination=destination,
        departure_time=datetime(2026, 8, 1, 10, 0),
        arrival_time=datetime(2026, 8, 1, 18, 0),
        price=500.0, seats_available=seats, aircraft_type=aircraft_type,
    )
    db.add(flight)
    db.commit()
    db.refresh(flight)
    fid = flight.id
    db.close()
    return fid


def flight_seats(flight_id):
    db = database.SessionLocal()
    seats = db.query(database.Flight).filter(
        database.Flight.id == flight_id).first().seats_available
    db.close()
    return seats


# --------------------------------------------------------------------------
# RES-01: booking
# --------------------------------------------------------------------------
def test_booking_requires_login():
    fid = seed_flight()
    c = TestClient(app)
    r = c.post("/api/bookings", json={"flight_id": fid})
    assert r.status_code == 401


def test_booking_creates_reservation_and_decrements_seats():
    fid = seed_flight()
    before = flight_seats(fid)
    c = login_client("booker@example.com")
    r = c.post("/api/bookings", json={"flight_id": fid, "seat": "14C"})
    assert r.status_code == 201
    body = r.json()
    assert len(body["booking_reference"]) == 6
    assert body["booking"]["status"] == "CONFIRMED"
    assert flight_seats(fid) == before - 1

    # The booking now shows up in the ongoing list.
    ongoing = c.get("/api/bookings/ongoing").json()
    assert any(b["seat"] == "14C" for b in ongoing)


def test_booking_unknown_flight_404():
    c = login_client("nf@example.com")
    r = c.post("/api/bookings", json={"flight_id": 99999})
    assert r.status_code == 404


def test_booking_invalid_seat_400():
    fid = seed_flight()
    c = login_client("badseat@example.com")
    r = c.post("/api/bookings", json={"flight_id": fid, "seat": "99Z"})
    assert r.status_code == 400


def test_booking_seat_taken_409():
    fid = seed_flight()
    c1 = login_client("first@example.com")
    c2 = login_client("second@example.com")
    assert c1.post("/api/bookings", json={"flight_id": fid, "seat": "12A"}).status_code == 201
    r = c2.post("/api/bookings", json={"flight_id": fid, "seat": "12A"})
    assert r.status_code == 409


def test_booking_flight_full_409():
    fid = seed_flight(flight_number="AC000", seats=0)
    c = login_client("full@example.com")
    r = c.post("/api/bookings", json={"flight_id": fid, "seat": "10A"})
    assert r.status_code == 409


# --------------------------------------------------------------------------
# RES-02: cancel
# --------------------------------------------------------------------------
def _book(client, flight_id, seat=None):
    r = client.post("/api/bookings", json={"flight_id": flight_id, "seat": seat})
    assert r.status_code == 201
    return r.json()["booking"]["id"]


def test_cancel_requires_login():
    c = TestClient(app)
    r = c.put("/api/bookings/1/cancel", json={"account_email": "x@example.com"})
    assert r.status_code == 401


def test_cancel_success_returns_verification_code_and_frees_seat():
    fid = seed_flight()
    c = login_client("amir@example.com")
    bid = _book(c, fid, "14C")
    seats_after_book = flight_seats(fid)

    r = c.put(f"/api/bookings/{bid}/cancel", json={"account_email": "amir@example.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["verification_code"] == f"CANCEL-BOOKING-{bid}"
    assert body["booking"]["status"] == "CANCELLED"
    assert body["booking"]["cancellation_timestamp"] is not None
    # Seat is returned to inventory.
    assert flight_seats(fid) == seats_after_book + 1


def test_cancel_wrong_confirmation_email_forbidden():
    fid = seed_flight()
    c = login_client("bilal@example.com")
    bid = _book(c, fid, "12A")
    r = c.put(f"/api/bookings/{bid}/cancel",
              json={"account_email": "someone-else@example.com"})
    assert r.status_code == 403


def test_cancel_already_cancelled_booking_rejected():
    fid = seed_flight()
    c = login_client("cara@example.com")
    bid = _book(c, fid, "12A")
    c.put(f"/api/bookings/{bid}/cancel", json={"account_email": "cara@example.com"})
    r = c.put(f"/api/bookings/{bid}/cancel", json={"account_email": "cara@example.com"})
    assert r.status_code == 400


def test_cancel_unknown_booking_not_found():
    c = login_client("dana@example.com")
    r = c.put("/api/bookings/999/cancel", json={"account_email": "dana@example.com"})
    assert r.status_code == 404


def test_cancel_other_users_booking_not_found():
    fid = seed_flight()
    owner = login_client("owner@example.com")
    bid = _book(owner, fid, "12A")
    intruder = login_client("intruder@example.com")
    r = intruder.put(f"/api/bookings/{bid}/cancel",
                     json={"account_email": "intruder@example.com"})
    assert r.status_code == 404


def test_cancelled_booking_moves_from_ongoing_to_cancelled():
    fid = seed_flight()
    c = login_client("emir@example.com")
    bid = _book(c, fid, "14C")

    ongoing_before = {b["id"] for b in c.get("/api/bookings/ongoing").json()}
    assert bid in ongoing_before

    c.put(f"/api/bookings/{bid}/cancel", json={"account_email": "emir@example.com"})

    ongoing_after = {b["id"] for b in c.get("/api/bookings/ongoing").json()}
    cancelled_after = {b["id"] for b in c.get("/api/bookings/cancelled").json()}
    assert bid not in ongoing_after
    assert bid in cancelled_after


# --------------------------------------------------------------------------
# RBAC + ADM-02: passenger list
# --------------------------------------------------------------------------
def test_customer_cannot_view_passenger_list_403():
    fid = seed_flight()
    c = login_client("plaincustomer@example.com")
    r = c.get(f"/api/flights/{fid}/passengers")
    assert r.status_code == 403


def test_admin_can_view_passenger_list_200():
    fid = seed_flight()
    # A customer books a seat so the manifest has an entry.
    pax = login_client("pax@example.com")
    pax.post("/api/bookings", json={
        "flight_id": fid, "seat": "14C",
        "special_accommodations": "Wheelchair assistance"})

    admin = login_client("admin@example.com")
    promote_to_admin("admin@example.com")
    r = admin.get(f"/api/flights/{fid}/passengers")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["passengers"][0]["seat"] == "14C"
    assert body["passengers"][0]["special_accommodations"] == "Wheelchair assistance"
    assert body["flight"]["capacity"] == len(aircraft.all_seats("A320"))


def test_seatmap_hides_names_for_customer_reveals_for_admin():
    fid = seed_flight()
    pax = login_client("named@example.com")
    # Give the passenger a profile so the admin view has a name to reveal.
    pax.post("/api/profile", json={
        "first_name": "Aisha", "last_name": "Khan", "phone": "2265550143",
        "address": "1 Sky Way", "city": "Toronto", "province": "Ontario"})
    pax.post("/api/bookings", json={"flight_id": fid, "seat": "14C"})

    def find_seat(payload, seat_id):
        for cabin in payload["cabins"]:
            for row in cabin["rows"]:
                for s in row["seats"]:
                    if s["seat"] == seat_id:
                        return s
        return None

    # Customer view: seat is occupied but carries no passenger identity.
    cust_map = pax.get(f"/api/flights/{fid}/seatmap").json()
    seat = find_seat(cust_map, "14C")
    assert seat["status"] == "occupied"
    assert "passenger" not in seat

    # Admin view: same seat now reveals the passenger + booking reference.
    admin = login_client("mapadmin@example.com")
    promote_to_admin("mapadmin@example.com")
    admin_map = admin.get(f"/api/flights/{fid}/seatmap").json()
    seat = find_seat(admin_map, "14C")
    assert seat["status"] == "occupied"
    assert seat["passenger"] == "Aisha Khan"
    assert "booking_reference" in seat
