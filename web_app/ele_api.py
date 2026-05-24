from flask import Flask, jsonify
from ensto_e import ElePrice
from read_energy_log import EnergyLogReader
from datetime import datetime
import ast
import os

example_response = {
    "2025-01-25T01:00:00+02:00": 0.279,
    "2025-01-25T02:00:00+02:00": 0.23199999999999998,
    "2025-01-25T03:00:00+02:00": 0.126,
    "2025-01-25T04:00:00+02:00": 0.101,
    "2025-01-25T05:00:00+02:00": 0.097,
    "2025-01-25T06:00:00+02:00": 0.074,
    "2025-01-25T07:00:00+02:00": 0.125,
    "2025-01-25T08:00:00+02:00": 0.22200000000000003,
    "2025-01-25T09:00:00+02:00": 0.279,
    "2025-01-25T10:00:00+02:00": 0.307,
    "2025-01-25T11:00:00+02:00": 0.291,
    "2025-01-25T12:00:00+02:00": 0.275,
    "2025-01-25T13:00:00+02:00": 0.295,
    "2025-01-25T14:00:00+02:00": 0.261,
    "2025-01-25T15:00:00+02:00": 0.25099999999999995,
    "2025-01-25T16:00:00+02:00": 0.216,
    "2025-01-25T17:00:00+02:00": 0.229,
    "2025-01-25T18:00:00+02:00": 0.2,
    "2025-01-25T19:00:00+02:00": 0.227,
    "2025-01-25T20:00:00+02:00": 0.194,
    "2025-01-25T21:00:00+02:00": 0.199,
    "2025-01-25T22:00:00+02:00": 0.176,
    "2025-01-25T23:00:00+02:00": 0.14,
    "2025-01-26T00:00:00+02:00": 0.026,
    "2025-01-26T01:00:00+02:00": 0.126,
    "2025-01-26T02:00:00+02:00": 0.121,
    "2025-01-26T03:00:00+02:00": 0.137,
    "2025-01-26T04:00:00+02:00": 0.145,
    "2025-01-26T05:00:00+02:00": 0.20099999999999998,
    "2025-01-26T06:00:00+02:00": 0.227,
    "2025-01-26T07:00:00+02:00": 0.216,
    "2025-01-26T08:00:00+02:00": 0.237,
    "2025-01-26T09:00:00+02:00": 0.238,
    "2025-01-26T10:00:00+02:00": 0.223,
    "2025-01-26T11:00:00+02:00": 0.279,
    "2025-01-26T12:00:00+02:00": 0.324,
    "2025-01-26T13:00:00+02:00": 0.4059999999999999,
    "2025-01-26T14:00:00+02:00": 0.463,
    "2025-01-26T15:00:00+02:00": 0.508,
    "2025-01-26T16:00:00+02:00": 1.716,
    "2025-01-26T17:00:00+02:00": 2.468,
    "2025-01-26T18:00:00+02:00": 3.7020000000000004,
    "2025-01-26T19:00:00+02:00": 4.434,
    "2025-01-26T20:00:00+02:00": 4.433,
    "2025-01-26T21:00:00+02:00": 3.8979999999999997,
    "2025-01-26T22:00:00+02:00": 4.542,
    "2025-01-26T23:00:00+02:00": 3.56,
    "2025-01-27T00:00:00+02:00": 2.692
}

example2 = {
    "current_time": "2025-01-27T00:00:00+02:00",
    "current_price": 2.54,
    "green_led": 1,
    "yellow_led": 1,
    "red_led": 0
}

energy_log_reader = EnergyLogReader()

# Initialize the Flask application
app = Flask(__name__)

# Define a single endpoint
@app.route('/api', methods=['GET'])
def api_endpoint():
    """A simple API endpoint that returns a JSON response."""
    # Construct the file path
    file_path = os.path.join(os.path.dirname(__file__), "price_info.py")

    with open(file_path, 'r') as file:
        file_content = file.read()

    # Convert the string content to a dictionary
    price_dict = ast.literal_eval(file_content)
    for key, value in price_dict.items():
        # Target ISO 8601 datetime string
        target_datetime_str = key

        # Parse the target datetime
        target_datetime = datetime.fromisoformat(target_datetime_str)

        # Get the current datetime in the same timezone
        current_datetime = datetime.now(target_datetime.tzinfo)

        # Check if the current datetime is in the same 15min as the target datetime
        is_same_hour = (
            current_datetime.year == target_datetime.year and
            current_datetime.month == target_datetime.month and
            current_datetime.day == target_datetime.day and
            current_datetime.hour == target_datetime.hour and
            (current_datetime.minute // 15) == (target_datetime.minute // 15)
        )
        price_to_send = 999
        if is_same_hour:
            price_to_send = value
            break
            #print(key, value)

    if price_to_send < 2:
        g_led = 1
        y_led = 0
        r_led = 0
    elif 2 <= price_to_send < 10:
        g_led = 0
        y_led = 1
        r_led = 0
    else:  # price_to_send >= 10
        g_led = 0
        y_led = 0
        r_led = 1
    
    latest_power_data = energy_log_reader.get_latest_data()

    response = {
        "current_time": target_datetime_str,
        "current_price": price_to_send,
        "green_led": g_led,
        "yellow_led": y_led,
        "red_led": r_led,
        "power": round(latest_power_data[2], 2),
        "avg_power": round(latest_power_data[1], 2),
    }

    #ele_price = ElePrice()
    #price_data = ele_price.get_price_info()
    #json_format = ele_price.format_price_to_dict(price_data)

    #print(json_format)
    #response = {
    #    "message": "Hello, World!",
    #    "status": "success",
    #    "data": None
    #}
    return jsonify(response)


# Run the application
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
