"""Focused ADM-01 API tests against the existing isolated SQLite test setup."""

import os
import sys
import pytest
from fastapi.testclient import TestClient

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
def fresh_db():
    database.Base.metadata.drop_all(bind=database.engine)
    database.Base.metadata.create_all(bind=database.engine)
    yield


def logged_in_client(email, admin=False):
    client = TestClient(app)
    password = "skyhigh12"
    client.post("/api/register", json={
        "email": email, "password": password, "confirm_password": password,
    })
    if admin:
        db = database.SessionLocal()
        user = db.query(database.User).filter(database.User.email == email).first()
        user.role = "admin"
        db.commit()
        db.close()
    client.post("/api/login", json={"email": email, "password": password})
    return client


def flight_payload(number="AC901", email="admin@air.ca", **overrides):
    payload = {
        "flight_number": number,
        "airline": "Air Canada",
        "origin": "Toronto",
        "destination": "Vancouver",
        "departure_time": "2026-10-01T10:00:00",
        "arrival_time": "2026-10-01T13:00:00",
        "price": 199.99,
        "seats_available": 120,
        "aircraft_type": "A320",
        "account_email": email,
    }
    payload.update(overrides)
    return payload


def create_flight(client, number="AC901", **overrides):
    response = client.post("/api/admin/flights", json=flight_payload(number, **overrides))
    assert response.status_code == 201
    return response.json()


def test_customer_cannot_list_admin_flights():
    customer = logged_in_client("customer@air.ca")
    assert customer.get("/api/admin/flights").status_code == 403


def test_customer_cannot_add_flight():
    customer = logged_in_client("customer@air.ca")
    assert customer.post("/api/admin/flights", json=flight_payload(email="customer@air.ca")).status_code == 403


def test_admin_can_list_flights():
    admin = logged_in_client("admin@air.ca", admin=True)
    create_flight(admin)
    response = admin.get("/api/admin/flights")
    assert response.status_code == 200
    assert response.json()[0]["flight_number"] == "AC901"


def test_admin_can_add_valid_flight_with_matching_email():
    admin = logged_in_client("admin@air.ca", admin=True)
    response = admin.post("/api/admin/flights", json=flight_payload(email=" ADMIN@AIR.CA "))
    assert response.status_code == 201
    assert response.json()["aircraft_type"] == "A320"


def test_add_fails_with_incorrect_admin_email():
    admin = logged_in_client("admin@air.ca", admin=True)
    assert admin.post("/api/admin/flights", json=flight_payload(email="other@air.ca")).status_code == 403


def test_duplicate_flight_number_fails():
    admin = logged_in_client("admin@air.ca", admin=True)
    create_flight(admin)
    assert admin.post("/api/admin/flights", json=flight_payload("ac901")).status_code == 409


def test_invalid_schedule_fails():
    admin = logged_in_client("admin@air.ca", admin=True)
    response = admin.post("/api/admin/flights", json=flight_payload(
        arrival_time="2026-10-01T09:00:00"))
    assert response.status_code == 400


def test_invalid_origin_destination_fails():
    admin = logged_in_client("admin@air.ca", admin=True)
    response = admin.post("/api/admin/flights", json=flight_payload(destination=" toronto "))
    assert response.status_code == 400


def test_seats_above_aircraft_capacity_fails():
    admin = logged_in_client("admin@air.ca", admin=True)
    response = admin.post("/api/admin/flights", json=flight_payload(
        seats_available=len(aircraft.all_seats("A320")) + 1))
    assert response.status_code == 400


def test_admin_can_update_flight():
    admin = logged_in_client("admin@air.ca", admin=True)
    flight = create_flight(admin)
    response = admin.put(f"/api/admin/flights/{flight['id']}", json=flight_payload(
        "AC901", price=245.50, seats_available=99))
    assert response.status_code == 200
    assert response.json()["price"] == 245.50
    assert response.json()["seats_available"] == 99


def test_update_fails_with_incorrect_email():
    admin = logged_in_client("admin@air.ca", admin=True)
    flight = create_flight(admin)
    response = admin.put(f"/api/admin/flights/{flight['id']}", json=flight_payload(
        "AC901", email="wrong@air.ca"))
    assert response.status_code == 403


def test_updating_nonexistent_flight_returns_404():
    admin = logged_in_client("admin@air.ca", admin=True)
    response = admin.put("/api/admin/flights/99999", json=flight_payload())
    assert response.status_code == 404


def test_admin_can_delete_unreserved_flight():
    admin = logged_in_client("admin@air.ca", admin=True)
    flight = create_flight(admin)
    response = admin.request("DELETE", f"/api/admin/flights/{flight['id']}", json={"account_email": "admin@air.ca"})
    assert response.status_code == 200
    assert admin.get("/api/admin/flights").json() == []


def test_delete_fails_with_incorrect_email():
    admin = logged_in_client("admin@air.ca", admin=True)
    flight = create_flight(admin)
    response = admin.request("DELETE", f"/api/admin/flights/{flight['id']}", json={"account_email": "wrong@air.ca"})
    assert response.status_code == 403


def test_deleting_flight_with_reservations_returns_409():
    admin = logged_in_client("admin@air.ca", admin=True)
    flight = create_flight(admin)
    db = database.SessionLocal()
    passenger = database.User(email="passenger@air.ca", password_hash="not-used")
    db.add(passenger)
    db.commit()
    db.add(database.Reservation(
        user_id=passenger.id, flight_id=flight["id"], booking_reference="ADM901",
        status="CONFIRMED",
    ))
    db.commit()
    db.close()
    response = admin.request("DELETE", f"/api/admin/flights/{flight['id']}", json={"account_email": "admin@air.ca"})
    assert response.status_code == 409


def test_customer_search_reflects_create_update_and_delete():
    admin = logged_in_client("admin@air.ca", admin=True)
    customer = logged_in_client("customer@air.ca")
    flight = create_flight(admin, "AC902")
    created = customer.get("/api/flights/search").json()
    assert any(item["id"] == flight["id"] for item in created)

    updated = admin.put(f"/api/admin/flights/{flight['id']}", json=flight_payload(
        "AC902", price=333.25, destination="Calgary"))
    assert updated.status_code == 200
    searched = customer.get("/api/flights/search").json()
    matching = next(item for item in searched if item["id"] == flight["id"])
    assert matching["destination"] == "Calgary"
    assert matching["price"] == 333.25

    deleted = admin.request("DELETE", f"/api/admin/flights/{flight['id']}", json={"account_email": "admin@air.ca"})
    assert deleted.status_code == 200
    assert all(item["id"] != flight["id"] for item in customer.get("/api/flights/search").json())
