"""
aircraft.py
-----------
Cabin layout configuration for the seat-map / passenger-list features
(ADM-02 View Passenger List and the RES-01 seat picker).

These are simplified but representative cabin configs — real airline layouts
vary by operator and sub-fleet; this is noted in the project report. A seat id
is ``f"{row}{column}"`` (e.g. "12A", "30K"). Each cabin defines its class name,
the row numbers it spans, the seat columns in physical left-to-right order, and
``aisles_after`` — the columns after which the UI inserts an aisle gap.
"""

# Each cabin may also declare (all optional, representative — real layouts vary):
#   extra_legroom_rows — bulkhead / exit rows sold as extra-legroom seats
#   preferred_rows     — front-of-cabin rows sold at a small premium
#   exit_rows          — rows adjacent to an over-wing / door exit (drawn on the map)
# Everything else in Economy is a Standard seat. These drive the seat-type
# colour coding on the visual seat map (like an airline fleet seat map).
AIRCRAFT_CONFIGS = {
    "A320": {
        "display_name": "Airbus A320 (narrowbody, single aisle)",
        "cabins": [
            {
                "class": "Business",
                "rows": list(range(1, 5)),          # rows 1–4
                "columns": ["A", "C", "D", "F"],    # 2-2
                "aisles_after": ["C"],
            },
            {
                "class": "Economy",
                "rows": list(range(10, 33)),        # rows 10–32
                "columns": ["A", "B", "C", "D", "E", "F"],  # 3-3
                "aisles_after": ["C"],
                "extra_legroom_rows": [10, 20, 21],  # bulkhead + over-wing exit
                "preferred_rows": [11, 12, 13, 14],
                "exit_rows": [20, 21],
            },
        ],
    },
    "B787": {
        "display_name": "Boeing 787-9 (widebody, twin aisle)",
        "cabins": [
            {
                "class": "Business",
                "rows": list(range(1, 8)),          # rows 1–7
                "columns": ["A", "C", "D", "G", "H", "K"],  # 2-2-2
                "aisles_after": ["C", "G"],
            },
            {
                "class": "Economy",
                # Note: nine-abreast 787 uses A B C | D E F | G H K (no "I").
                "rows": list(range(30, 59)),        # rows 30–58
                "columns": ["A", "B", "C", "D", "E", "F", "G", "H", "K"],  # 3-3-3
                "aisles_after": ["C", "F"],
                "extra_legroom_rows": [30, 44, 45],  # bulkhead + mid-cabin exits
                "preferred_rows": [31, 32, 33, 34],
                "exit_rows": [44, 45],
            },
        ],
    },
}


def all_seats(aircraft_type: str):
    """Return an ordered list of every seat id for an aircraft type."""
    cfg = AIRCRAFT_CONFIGS.get(aircraft_type) or AIRCRAFT_CONFIGS["A320"]
    seats = []
    for cabin in cfg["cabins"]:
        for row in cabin["rows"]:
            for col in cabin["columns"]:
                seats.append(f"{row}{col}")
    return seats


def seat_class(aircraft_type: str, seat: str):
    """Return the cabin class a given seat belongs to, or None if invalid."""
    cfg = AIRCRAFT_CONFIGS.get(aircraft_type) or AIRCRAFT_CONFIGS["A320"]
    for cabin in cfg["cabins"]:
        row_part = "".join(ch for ch in seat if ch.isdigit())
        col_part = "".join(ch for ch in seat if ch.isalpha())
        if row_part and int(row_part) in cabin["rows"] and col_part in cabin["columns"]:
            return cabin["class"]
    return None


def seat_type(aircraft_type: str, seat: str):
    """
    Return the fare/seat *type* for colour coding on the visual map, one of
    "business" | "extra_legroom" | "preferred" | "standard", or None if the
    seat id is not valid for this aircraft.
    """
    cfg = AIRCRAFT_CONFIGS.get(aircraft_type) or AIRCRAFT_CONFIGS["A320"]
    for cabin in cfg["cabins"]:
        row_part = "".join(ch for ch in seat if ch.isdigit())
        col_part = "".join(ch for ch in seat if ch.isalpha())
        if not (row_part and int(row_part) in cabin["rows"] and col_part in cabin["columns"]):
            continue
        row = int(row_part)
        if cabin["class"] == "Business":
            return "business"
        if row in cabin.get("extra_legroom_rows", []):
            return "extra_legroom"
        if row in cabin.get("preferred_rows", []):
            return "preferred"
        return "standard"
    return None
