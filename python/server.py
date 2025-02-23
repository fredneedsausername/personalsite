from flask import Flask, render_template, request, jsonify
import fredbconn
import json
from datetime import datetime
import locale
from waitress import serve
import passwords
import logging
import sys
import os
import traceback


app = Flask(__name__, template_folder = "../templates", static_folder = "../static")

@fredbconn.connected_to_database
def associate_arduino_name_to_ids(cursor, arduino_name: str) -> int | None:
        cursor.execute(f"""
        SELECT id
        FROM ArduinoDevices
        WHERE device_name = %s;
        """, (arduino_name,))
        fetched = cursor.fetchone()
        return None if fetched is None else fetched[0]


class MeasurementReceived:
    
    def __init__(self, arduinos_temperature: float, arduinos_relative_humidity: int, arduinos_name: str):
        self.temperature = round(float(arduinos_temperature), 1)
        self.relative_humidity = int(arduinos_relative_humidity)
        self.id = associate_arduino_name_to_ids(arduinos_name)
    

    @classmethod
    def from_json_and_name(cls, json, arduinos_name: str):
        return cls(json["temperature"], json["relative-humidity"], arduinos_name)


class Measurement:
    
    def __init__(self, date: datetime, arduinos_temperature: float, arduinos_relative_humidity: int, arduinos_id: int):
        self.date = date
        self.temperature = round(float(arduinos_temperature), 1)
        self.relative_humidity = int(arduinos_relative_humidity)
        self.id = arduinos_id


    @classmethod
    def from_database_query(cls, returned):
        return cls(returned[0], float(returned[1]), returned[2], returned[3])
        # (datetime.datetime(2025, 1, 4, 12, 30, 45), Decimal('23.5'), 60, 1)
    

    def __repr__(self):
        return str(self.date) + " " + str(self.temperature) + " " + str(self.relative_humidity) + " " + str(self.id)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/storia-progetto-arduino")
def storia_progetto_arduino():
    return render_template("storia-progetto-arduino.html")

@app.route("/corso-c")
def corso_c():
    return render_template("corso-c.html")


@app.route("/sensor-endpoint", methods = ["POST"])
@fredbconn.connected_to_database
def receive_data(cursor):

    sender_name = request.headers.get('Arduino-Name')
    if sender_name is None: return jsonify({"error": "Missing Arduino-Name header"}), 400

    sender_password = request.headers.get('Arduino-Password')
    if sender_password is None: return jsonify({"error": "Missing Arduino-Password header"}), 400

    if associate_arduino_name_to_ids(sender_name) is None: return jsonify({"error": "Arduino name not recognized"}), 400

    cursor.execute(f"""
    SELECT device_password
    FROM ArduinoDevices
    WHERE device_name = %s;
    """, (sender_name,))

    retrieved_password_tuple = cursor.fetchone()

    if retrieved_password_tuple is None: return jsonify({"error": "Unregistered Arduino name"}), 404

    retrieved_password = retrieved_password_tuple[0]

    json_body = request.get_json(silent = False) # automatically returns an error if it is not valid json

    measurement = MeasurementReceived.from_json_and_name(json_body, sender_name)

    if retrieved_password == sender_password:
        cursor.execute("""
        INSERT INTO Measurements (measurement_time, temperature_celsius, humidity_percentage, device_id)
        VALUES (NOW(), %s, %s, %s);
        """, (measurement.temperature, measurement.relative_humidity, measurement.id))
        if cursor.rowcount > 0: return jsonify({"message": "Measurement recorded successfully"}), 200
        else: return jsonify({"error": "Measurement insertion into the database failed"}), 500
    else:
        return jsonify({"error": "Invalid password"}), 401


@app.route("/api/arduino-names")
@fredbconn.connected_to_database
def give_arduino_names(cursor):

    arduino_names = []

    cursor.execute("""
    SELECT device_name
    FROM ArduinoDevices;
    """)

    while arduino_name := cursor.fetchone(): arduino_names.append(arduino_name[0])

    return jsonify(arduino_names)


@app.route("/api/earliest-latest-arduino-measurements-dates", methods = ["POST"])
@fredbconn.connected_to_database
def give_earliest_and_latest_arduino_measurements_dates(cursor):

    json_body = request.get_json(silent = False) # automatically returns an error if it is not valid json

    arduino_name = json_body.get("arduino_name")
    if arduino_name is None: return jsonify({"error": "Missing field arduino_name in json body"}), 400

    arduino_id = associate_arduino_name_to_ids(arduino_name)

    if(not arduino_id): return jsonify({"error": "Unregistered Arduino name"}), 404

    cursor.execute("""
    SELECT measurement_time, temperature_celsius, humidity_percentage, device_id
    FROM Measurements
    WHERE device_id = %s
    AND measurement_time = (
        SELECT MIN(measurement_time)
        FROM Measurements
        WHERE device_id = %s
    );
    """, (arduino_id, arduino_id))

    earliest_measurement_query_result = cursor.fetchone()

    if(not earliest_measurement_query_result): return jsonify({"error": "No measurements found"}), 404 

    earliest_measurement_date = (Measurement.from_database_query(earliest_measurement_query_result)).date.date().isoformat()

    cursor.execute("""
    SELECT measurement_time, temperature_celsius, humidity_percentage, device_id
    FROM Measurements
    WHERE device_id = %s
    AND measurement_time = (
        SELECT MAX(measurement_time)
        FROM Measurements
        WHERE device_id = %s
    );
    """, (arduino_id, arduino_id))

    # will always yield because otherwise it wouldn't have when we asked it for the earliest measurement
    latest_measurement_query_result = cursor.fetchone() 
    latest_measurement_date = Measurement.from_database_query(latest_measurement_query_result).date.date().isoformat()

    return jsonify ({
        "earliest_measurement_date": earliest_measurement_date, 
        "latest_measurement_date": latest_measurement_date
    })


@app.route("/api/arduino-measurements", methods = ["POST"])
@fredbconn.connected_to_database
def give_arduino_measurements(cursor):

    def is_valid_date_YYYYdashMMdashDD(date_string: str) -> bool:
        try:
            datetime.strptime(date_string, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    body = request.get_json(silent = False) # automatically returns an error if it is not valid json

    arduino_name = body.get("arduino_name")
    if arduino_name is None: return jsonify({"error": "Missing field arduino_name in json body"}), 400

    start_date = body.get("start_date")
    if start_date is None: return jsonify({"error": "Missing field start_date in json body"}), 400

    end_date = body.get("end_date")
    if end_date is None: return jsonify({"error": "Missing field start_date in json body"}), 400

    received_date_format = "%Y-%m-%d"

    if not is_valid_date_YYYYdashMMdashDD(start_date): return jsonify({"error": "Invalid format of start_date field in json body"}), 400
    if not is_valid_date_YYYYdashMMdashDD(end_date): return jsonify({"error": "Invalid format of end_date field in json body"}), 400

    d1 = datetime.strptime(start_date, received_date_format)
    d2 = datetime.strptime(end_date, received_date_format)

    if (d2 - d1).days > 7: return jsonify({"error": "Maximum days range is 7"}), 400

    arduino_id = associate_arduino_name_to_ids(arduino_name)

    if not arduino_id: return jsonify({"error": "No Arduino found with that name"}), 404

    cursor.execute("""
    SELECT measurement_time, temperature_celsius, humidity_percentage, device_id
    FROM Measurements
    WHERE measurement_time BETWEEN %s AND %s
    AND device_id = %s;
    """, (d1, d2, arduino_id))

    dates = []
    temperatures = []
    humidity = []

    while query_result := cursor.fetchone():
        measurement = Measurement.from_database_query(query_result)

        dates.append(f"{measurement.date.day} {measurement.date.strftime('%b %H:%M')}")
        temperatures.append(measurement.temperature)
        humidity.append(measurement.relative_humidity)
    
    return jsonify({
        "dates": dates,
        "temperatures": temperatures,
        "humidity": humidity
    })

if __name__ == "__main__":
    fredbconn.initialize_database(*passwords.database_config)
    locale.setlocale(locale.LC_TIME, 'it_IT.UTF-8')

    class CrashLogger:
        def __init__(self, log_dir="/var/log/sitofred", log_filename=None):
            """
            Initializes the crash logger.
            
            :param log_dir: Directory where logs will be stored.
            :param log_filename: Custom log file name (default: auto-generated with timestamp).
            """
            self.log_dir = log_dir
            os.makedirs(self.log_dir, exist_ok=True)  # Ensure directory exists
            
            # Generate a log filename if not provided
            if log_filename is None:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                log_filename = f"error_{timestamp}.log"
            
            self.log_file = os.path.join(self.log_dir, log_filename)
            
            # Configure logging
            logging.basicConfig(
                filename=self.log_file,
                level=logging.ERROR,
                format="%(asctime)s - %(levelname)s - %(message)s",
            )

            # Set the global exception hook
            sys.excepthook = self.log_exception

        def log_exception(self, exc_type, exc_value, exc_traceback):
            """
            Logs uncaught exceptions.
            """
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logging.error("Unhandled Exception:\n" + error_message)

        def log_custom_error(self, message):
            """
            Allows manual logging of error messages.
            """
            logging.error(message)

    # Initialize logger
    crash_logger = CrashLogger()

    # Set the crash logs custom error
    crash_logger.log_custom_error("ERROR")

    serve(app, host="127.0.0.1", port=42069)