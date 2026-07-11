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
