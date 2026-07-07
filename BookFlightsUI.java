import javax.swing.*;
import java.awt.*;
import java.util.HashMap;

public class BookFlightsUI extends JFrame {

    // Color Palette
    private static final Color BLUE = Color.decode("#597f97");
    private static final Color LIGHT_BLUE = Color.decode("#c4cbd8");
    private static final Color GRAY = Color.decode("#6c747c");
    private static final Color NAVY = Color.decode("#183251");
    private static final Color OFF_WHITE = Color.decode("#c8c4c4");

    private JTextField fromField, toField;
    private JTextArea resultsArea;
    private HashMap<String, Flight> flights = new HashMap<>();

    static class Flight {
        String code, airline, from, to, date, time;
        double price;
        int seats;

        Flight(String code, String airline, String from, String to, String date, String time, double price, int seats) {
            this.code = code;
            this.airline = airline;
            this.from = from;
            this.to = to;
            this.date = date;
            this.time = time;
            this.price = price;
            this.seats = seats;
        }

        public String toString() {
            return code + " | " + airline + " | " + from + " to " + to +
                    " | " + date + " | " + time + " | $" + price +
                    " | Seats: " + seats;
        }
    }

    public BookFlightsUI() {
        setTitle("Book Flights");
        setSize(500, 550);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLocationRelativeTo(null);

        flights.put("AC101", new Flight("AC101", "Air Canada", "Toronto", "Vancouver", "2026-07-05", "9:00 AM", 350, 5));
        flights.put("WS205", new Flight("WS205", "WestJet", "Toronto", "Calgary", "2026-07-05", "1:30 PM", 280, 3));
        flights.put("PD330", new Flight("PD330", "Porter", "Toronto", "Ottawa", "2026-07-06", "11:15 AM", 180, 4));

        JPanel panel = new JPanel();
        panel.setLayout(null);
        panel.setBackground(NAVY);
        add(panel);

        JLabel title = new JLabel("Book Flights");
        title.setBounds(160, 35, 250, 40);
        title.setFont(new Font("Arial", Font.BOLD, 28));
        title.setForeground(OFF_WHITE);
        panel.add(title);

        JLabel fromLabel = new JLabel("Departure City");
        fromLabel.setBounds(90, 110, 200, 25);
        fromLabel.setForeground(OFF_WHITE);
        panel.add(fromLabel);

        fromField = new JTextField();
        fromField.setBounds(90, 140, 300, 32);
        fromField.setBackground(LIGHT_BLUE);
        fromField.setForeground(NAVY);
        fromField.setCaretColor(NAVY);
        panel.add(fromField);

        JLabel toLabel = new JLabel("Destination City");
        toLabel.setBounds(90, 185, 200, 25);
        toLabel.setForeground(OFF_WHITE);
        panel.add(toLabel);

        toField = new JTextField();
        toField.setBounds(90, 215, 300, 32);
        toField.setBackground(LIGHT_BLUE);
        toField.setForeground(NAVY);
        toField.setCaretColor(NAVY);
        panel.add(toField);

        JButton searchButton = new JButton("Search Flights");
        searchButton.setBounds(160, 270, 160, 38);
        searchButton.setBackground(BLUE);
        searchButton.setForeground(Color.WHITE);
        searchButton.setFocusPainted(false);
        panel.add(searchButton);

        resultsArea = new JTextArea();
        resultsArea.setBounds(50, 330, 390, 130);
        resultsArea.setBackground(OFF_WHITE);
        resultsArea.setForeground(NAVY);
        resultsArea.setCaretColor(NAVY);
        resultsArea.setEditable(false);
        resultsArea.setLineWrap(true);
        panel.add(resultsArea);

        JButton bookButton = new JButton("Book Selected Flight");
        bookButton.setBounds(140, 470, 200, 35);
        bookButton.setBackground(GRAY);
        bookButton.setForeground(Color.WHITE);
        bookButton.setFocusPainted(false);
        panel.add(bookButton);

        searchButton.addActionListener(e -> searchFlights());
        bookButton.addActionListener(e -> bookFlight());
    }

    private void searchFlights() {
        String from = fromField.getText();
        String to = toField.getText();

        resultsArea.setText("");

        for (Flight flight : flights.values()) {
            if (flight.from.equalsIgnoreCase(from)
                    && flight.to.equalsIgnoreCase(to)
                    && flight.seats > 0) {
                resultsArea.append(flight.toString() + "\n\n");
            }
        }

        if (resultsArea.getText().isEmpty()) {
            resultsArea.setText("No flights found.");
        }
    }

    private void bookFlight() {
        String text = resultsArea.getText();

        if (text.contains("AC101")) {
            flights.get("AC101").seats--;
            JOptionPane.showMessageDialog(this, "Flight AC101 booked successfully!");
        } else if (text.contains("WS205")) {
            flights.get("WS205").seats--;
            JOptionPane.showMessageDialog(this, "Flight WS205 booked successfully!");
        } else if (text.contains("PD330")) {
            flights.get("PD330").seats--;
            JOptionPane.showMessageDialog(this, "Flight PD330 booked successfully!");
        } else {
            JOptionPane.showMessageDialog(this, "Please search for a flight first.");
        }

        searchFlights();
    }

    public static void main(String[] args) {
        new BookFlightsUI().setVisible(true);
    }
}