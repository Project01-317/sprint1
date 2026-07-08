import tkinter as tk
from tkinter import messagebox


class Flight:
    def __init__(self, code, airline, departure, destination, date, time, price, seats):
        self.code = code
        self.airline = airline
        self.departure = departure
        self.destination = destination
        self.date = date
        self.time = time
        self.price = price
        self.seats = seats

    def __str__(self):
        return (f"{self.code} | {self.airline} | {self.departure} to "
                f"{self.destination} | {self.date} | {self.time} | "
                f"${self.price} | Seats: {self.seats}")


class BookFlightsUI:

    # Color Palette
    BLUE = "#597f97"
    LIGHT_BLUE = "#c4cbd8"
    GRAY = "#6c747c"
    NAVY = "#183251"
    OFF_WHITE = "#c8c4c4"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Book Flights")
        self.root.geometry("500x550")
        self.root.configure(bg=self.NAVY)
        self.root.resizable(False, False)

        # Flight database
        self.flights = {
            "AC101": Flight("AC101", "Air Canada", "Toronto", "Vancouver",
                            "2026-07-05", "9:00 AM", 350, 5),

            "WS205": Flight("WS205", "WestJet", "Toronto", "Calgary",
                            "2026-07-05", "1:30 PM", 280, 3),

            "PD330": Flight("PD330", "Porter", "Toronto", "Ottawa",
                            "2026-07-06", "11:15 AM", 180, 4)
        }

        # Title
        title = tk.Label(self.root,
                         text="Book Flights",
                         font=("Arial", 28, "bold"),
                         bg=self.NAVY,
                         fg=self.OFF_WHITE)
        title.place(x=140, y=30)

        # Departure
        tk.Label(self.root,
                 text="Departure City",
                 bg=self.NAVY,
                 fg=self.OFF_WHITE).place(x=90, y=110)

        self.from_entry = tk.Entry(self.root,
                                   bg=self.LIGHT_BLUE,
                                   fg=self.NAVY)
        self.from_entry.place(x=90, y=140, width=300, height=32)

        # Destination
        tk.Label(self.root,
                 text="Destination City",
                 bg=self.NAVY,
                 fg=self.OFF_WHITE).place(x=90, y=185)

        self.to_entry = tk.Entry(self.root,
                                 bg=self.LIGHT_BLUE,
                                 fg=self.NAVY)
        self.to_entry.place(x=90, y=215, width=300, height=32)

        # Search Button
        search_btn = tk.Button(
            self.root,
            text="Search Flights",
            bg=self.BLUE,
            fg="white",
            command=self.search_flights
        )
        search_btn.place(x=160, y=270, width=160, height=38)

        # Results
        self.results = tk.Text(
            self.root,
            bg=self.OFF_WHITE,
            fg=self.NAVY,
            wrap="word"
        )
        self.results.place(x=50, y=330, width=390, height=130)

        # Book Button
        book_btn = tk.Button(
            self.root,
            text="Book Selected Flight",
            bg=self.GRAY,
            fg="white",
            command=self.book_flight
        )
        book_btn.place(x=140, y=470, width=200, height=35)

    def search_flights(self):
        departure = self.from_entry.get()
        destination = self.to_entry.get()

        self.results.delete("1.0", tk.END)

        found = False

        for flight in self.flights.values():
            if (flight.departure.lower() == departure.lower() and
                    flight.destination.lower() == destination.lower() and
                    flight.seats > 0):

                self.results.insert(tk.END, str(flight) + "\n\n")
                found = True

        if not found:
            self.results.insert(tk.END, "No flights found.")

    def book_flight(self):
        text = self.results.get("1.0", tk.END)

        if "AC101" in text:
            self.flights["AC101"].seats -= 1
            messagebox.showinfo("Success", "Flight AC101 booked successfully!")

        elif "WS205" in text:
            self.flights["WS205"].seats -= 1
            messagebox.showinfo("Success", "Flight WS205 booked successfully!")

        elif "PD330" in text:
            self.flights["PD330"].seats -= 1
            messagebox.showinfo("Success", "Flight PD330 booked successfully!")

        else:
            messagebox.showinfo("Notice", "Please search for a flight first.")

        self.search_flights()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = BookFlightsUI()
    app.run()