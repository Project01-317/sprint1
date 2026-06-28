"""
test_auth.py — automated tests for ACC-01 (User Login).

Each test maps to a row in the Sprint 1 Testing & Review table. Run with:
    pytest -v
"""

import os
import sys

import pytest
from fastapi.testclient import TestClient

# Make sure we use a throwaway database for tests, not the dev one.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import backend.database as database  # noqa: E402

TEST_DB = "sqlite:///./test_airline.db"
database.engine = database.create_engine(
    TEST_DB, connect_args={"check_same_thread": False}
)
database.SessionLocal.configure(bind=database.engine)

from backend.main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_db():
    database.Base.metadata.drop_all(bind=database.engine)
    database.Base.metadata.create_all(bind=database.engine)
    yield


def test_register_success():
    r = client.post("/api/register", json={
        "email": "alice@example.com", "password": "skyhigh12",
        "confirm_password": "skyhigh12"})
    assert r.status_code == 200


def test_register_duplicate_email():
    payload = {"email": "bob@example.com", "password": "skyhigh12",
               "confirm_password": "skyhigh12"}
    client.post("/api/register", json=payload)
    r = client.post("/api/register", json=payload)
    assert r.status_code == 409


def test_register_password_mismatch():
    r = client.post("/api/register", json={
        "email": "carol@example.com", "password": "skyhigh12",
        "confirm_password": "different1"})
    assert r.status_code == 400


def test_register_short_password():
    r = client.post("/api/register", json={
        "email": "dan@example.com", "password": "short", "confirm_password": "short"})
    assert r.status_code == 400


def test_register_invalid_email():
    r = client.post("/api/register", json={
        "email": "not-an-email", "password": "skyhigh12",
        "confirm_password": "skyhigh12"})
    assert r.status_code == 400


def test_login_success_routes_to_profile_first():
    client.post("/api/register", json={
        "email": "eve@example.com", "password": "skyhigh12",
        "confirm_password": "skyhigh12"})
    r = client.post("/api/login", json={
        "email": "eve@example.com", "password": "skyhigh12"})
    assert r.status_code == 200
    assert r.json()["next_screen"] == "profile"


def test_login_wrong_password():
    client.post("/api/register", json={
        "email": "frank@example.com", "password": "skyhigh12",
        "confirm_password": "skyhigh12"})
    r = client.post("/api/login", json={
        "email": "frank@example.com", "password": "wrongpass1"})
    assert r.status_code == 401


def test_login_unknown_email():
    r = client.post("/api/login", json={
        "email": "ghost@example.com", "password": "skyhigh12"})
    assert r.status_code == 401


def test_profile_save_then_login_skips_setup():
    c = TestClient(app)
    c.post("/api/register", json={
        "email": "grace@example.com", "password": "skyhigh12",
        "confirm_password": "skyhigh12"})
    c.post("/api/login", json={"email": "grace@example.com", "password": "skyhigh12"})
    r = c.post("/api/profile", json={
        "first_name": "Grace", "last_name": "Hopper", "phone": "2265550143",
        "address": "1 Navy Way", "city": "Waterloo", "province": "Ontario"})
    assert r.status_code == 200
    # Re-login should now route straight to the dashboard.
    r2 = c.post("/api/login", json={"email": "grace@example.com", "password": "skyhigh12"})
    assert r2.json()["next_screen"] == "dashboard"


def test_password_is_hashed_not_plaintext():
    client.post("/api/register", json={
        "email": "heidi@example.com", "password": "skyhigh12",
        "confirm_password": "skyhigh12"})
    db = database.SessionLocal()
    user = db.query(database.User).filter(
        database.User.email == "heidi@example.com").first()
    db.close()
    assert user.password_hash != "skyhigh12"
    assert user.password_hash.startswith("$argon2id$")  # Argon2id prefix
