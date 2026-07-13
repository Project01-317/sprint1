"""
seed_reservations.py
--------------------
Seed an admin account, a few customer accounts with profiles, and several
CONFIRMED reservations so the passenger list (ADM-02) and seat map have data
to show immediately.

Run AFTER seed_flights.py (it needs real flights to book against):
    python seed_flights.py
    python seed_reservations.py

Test credentials created here:
    admin    -> admin@air.ca      / admin1234
    customer -> aisha@air.ca      / skyhigh12   (and a few more, same password)
"""

from datetime import datetime, timedelta

from backend.database import SessionLocal, Flight, User, UserProfile, Reservation, init_db
from backend.auth import hash_password
from backend import aircraft

CUSTOMER_PASSWORD = "skyhigh12"

# (email, first, last, phone, city, seat, accommodations)
CUSTOMERS = [
    ("aisha@air.ca", "Aisha", "Khan", "2265550111", "Toronto", "14C", "Wheelchair assistance"),
    ("marco@air.ca", "Marco", "Rossi", "2265550112", "Montreal", "12A", None),
    ("wei@air.ca", "Wei", "Chen", "2265550113", "Vancouver", "15D", None),
    ("sara@air.ca", "Sara", "Ahmed", "2265550114", "Calgary", "10B", "Dietary: vegetarian meal"),
    ("liam@air.ca", "Liam", "Obrien", "2265550115", "Ottawa", "22F", None),
]


def get_or_create_user(db, email, password, role="customer"):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, password_hash=hash_password(password), role=role)
        db.add(user)
        db.flush()
    return user


def seed():
    init_db()
    db = SessionLocal()

    # 1. Admin account.
    get_or_create_user(db, "admin@air.ca", "admin1234", role="admin")

    # Pick two real flights to populate. Prefer an A320 and a B787 so both
    # seat-map layouts have data.
    flights = db.query(Flight).order_by(Flight.id.asc()).all()
    if not flights:
        print("No flights found. Run `python seed_flights.py` first.")
        db.close()
        return

    a320 = next((f for f in flights if f.aircraft_type == "A320"), flights[0])
    b787 = next((f for f in flights if f.aircraft_type == "B787"), flights[-1])
    target_flights = [a320, b787]

    created = 0
    for idx, (email, first, last, phone, city, seat, accom) in enumerate(CUSTOMERS):
        user = get_or_create_user(db, email, CUSTOMER_PASSWORD)
        if user.profile is None:
            user.profile = UserProfile(
                user_id=user.id, first_name=first, last_name=last,
                phone=phone, address="1 Airport Rd", city=city, province="Ontario",
            )
            db.flush()

        flight = target_flights[idx % len(target_flights)]
        # Validate the seat against the chosen flight; fall back to the first
        # available seat if the hardcoded one is not on this aircraft type.
        if aircraft.seat_class(flight.aircraft_type, seat) is None:
            seat = aircraft.all_seats(flight.aircraft_type)[idx]

        # Skip if this seat is already taken on this flight (idempotent reseed).
        exists = db.query(Reservation).filter(
            Reservation.flight_id == flight.id,
            Reservation.seat == seat,
            Reservation.status == "CONFIRMED",
        ).first()
        if exists:
            continue

        reservation = Reservation(
            user_id=user.id,
            flight_id=flight.id,
            booking_reference=f"SEED{idx:02d}",
            seat=seat,
            status="CONFIRMED",
            special_accommodations=accom,
        )
        flight.seats_available = max(0, flight.seats_available - 1)
        db.add(reservation)
        created += 1

    # A past-dated flight + reservation so ACC-02's "Past" tab (and a past
    # e-ticket) have data. Seeded flights are otherwise future/near-dated.
    past_flight = db.query(Flight).filter(Flight.flight_number == "G15PAST").first()
    if past_flight is None:
        dep = datetime.now() - timedelta(days=6)
        past_flight = Flight(
            flight_number="G15PAST", airline="Group 15 Air",
            origin="Toronto", destination="Vancouver",
            departure_time=dep, arrival_time=dep + timedelta(hours=5),
            price=349.0, seats_available=len(aircraft.all_seats("A320")),
            aircraft_type="A320",
        )
        db.add(past_flight)
        db.flush()
    aisha = db.query(User).filter(User.email == "aisha@air.ca").first()
    already_past = db.query(Reservation).filter(
        Reservation.flight_id == past_flight.id,
        Reservation.booking_reference == "SEEDPAST",
    ).first()
    if aisha and not already_past:
        db.add(Reservation(
            user_id=aisha.id, flight_id=past_flight.id,
            booking_reference="SEEDPAST", seat="12A", status="CONFIRMED",
        ))
        past_flight.seats_available = max(0, past_flight.seats_available - 1)
        created += 1

    db.commit()
    print(f"Seeded admin + {len(CUSTOMERS)} customers and {created} reservations.")
    print(f"  Flights populated: {a320.flight_number} (A320), {b787.flight_number} (B787)")
    print(f"  Past-dated demo flight: {past_flight.flight_number} (reservation for aisha@air.ca)")
    db.close()


if __name__ == "__main__":
    seed()
