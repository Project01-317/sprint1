import random
from datetime import datetime, timedelta
from backend.database import SessionLocal, Flight, init_db
from backend import aircraft

# Pool of realistic data to randomize from
AIRLINES = [
    ("AC", "Air Canada"), ("WS", "WestJet"), ("DL", "Delta Airlines"), 
    ("UA", "United Airlines"), ("AA", "American Airlines"), ("EK", "Emirates"),
    ("BA", "British Airways"), ("LH", "Lufthansa"), ("AF", "Air France")
]

CITIES = [
    "Toronto", "Vancouver", "Montreal", "Calgary", 
    "New York", "Los Angeles", "Chicago", "Miami", 
    "London", "Paris", "Dubai", "Tokyo", "Frankfurt"
]

AIRCRAFT_TYPES = ["A320", "B787"]


def generate_random_flights(num_flights=150):
    # Create tables first — on a clean checkout there is no airline.db yet, so
    # inserting before the schema exists used to crash the seed.
    init_db()

    db = SessionLocal()
    flights_to_add = []
    used_flight_numbers = set()
    
    # Start generating flights from July 1, 2026
    start_date = datetime(2026, 7, 1, 5, 0)
    
    for _ in range(num_flights):
        # Pick airline and cities
        airline_code, airline_name = random.choice(AIRLINES)
        origin = random.choice(CITIES)
        destination = random.choice(CITIES)
        
        # Ensure origin and destination aren't the same
        while destination == origin:
            destination = random.choice(CITIES)
            
        # Guarantee unique flight numbers
        while True:
            flight_num = f"{airline_code}{random.randint(100, 9999)}"
            if flight_num not in used_flight_numbers:
                used_flight_numbers.add(flight_num)
                break
                
        # Randomize departure time (sometime in July 2026)
        days_offset = random.randint(0, 30)
        hours_offset = random.randint(0, 18)
        minutes_offset = random.choice([0, 15, 30, 45])
        departure_time = start_date + timedelta(days=days_offset, hours=hours_offset, minutes=minutes_offset)
        
        # Randomize duration (1 to 14 hours) to calculate arrival
        duration_minutes = random.randint(60, 14 * 60)
        arrival_time = departure_time + timedelta(minutes=duration_minutes)
        
        # Randomize price ($99.00 to $1299.00)
        price = round(random.uniform(99.0, 1299.0), 2)

        # Pick an aircraft type and set seats_available to the config's real
        # seat count so search/booking inventory matches the seat map.
        aircraft_type = random.choice(AIRCRAFT_TYPES)
        seats = len(aircraft.all_seats(aircraft_type))

        flight = Flight(
            flight_number=flight_num,
            airline=airline_name,
            origin=origin,
            destination=destination,
            departure_time=departure_time,
            arrival_time=arrival_time,
            price=price,
            seats_available=seats,
            aircraft_type=aircraft_type,
        )
        flights_to_add.append(flight)
        
    db.add_all(flights_to_add)
    db.commit()
    db.close()
    
    print(f"Successfully seeded {num_flights} random flights into the database.")

if __name__ == "__main__":
    # Clear out old test data first if you want a clean slate
    # db = SessionLocal()
    # db.query(Flight).delete()
    # db.commit()
    # db.close()
    
    generate_random_flights(150)