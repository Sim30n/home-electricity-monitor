import requests
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import json
import pytz
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class ElePrice:
    def __init__(self):
        pass

    def get_price_info(self):

        # Define your datetime objects
        period_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(hours=24)  # 24 hours forward

        security_token = os.getenv('SECURITY_TOKEN')

        base_url = (
            "https://web-api.tp.entsoe.eu/api"
            "?documentType=A44"
            "&periodStart={periodStart}"
            "&periodEnd={periodEnd}"
            "&out_Domain=10YFI-1--------U"
            "&in_Domain=10YFI-1--------U"
            f"&securityToken={security_token}"
        )
        # Replace placeholders with formatted datetime values
        url = base_url.format(
            periodStart=period_start.strftime('%Y%m%d%H%M'),
            periodEnd=period_end.strftime('%Y%m%d%H%M')
        )
        payload = {}
        headers = {}
        response = requests.request("GET", url, headers=headers, data=payload)
        return response

    def parse_duration(self, duration):
        """Helper function to parse ISO 8601 duration (e.g., PT60M)

        """
        if duration.startswith("PT") and "M" in duration:
            minutes = int(duration.replace("PT", "").replace("M", ""))
            return timedelta(minutes=minutes)
        return timedelta()

    def format_price_to_dict(self, response):

        # Register the namespace
        namespace = {"ns": "urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3"}

        # Parse the XML
        root = ET.fromstring(response.text)

        # Extract TimeSeries data
        time_series = []
        for ts in root.findall("ns:TimeSeries", namespace):
            ts_data = {
                "mRID": ts.find("ns:mRID", namespace).text,
                "auction_type": ts.find("ns:auction.type", namespace).text,
                "business_type": ts.find("ns:businessType", namespace).text,
                "currency": ts.find("ns:currency_Unit.name", namespace).text,
                "price_unit": ts.find("ns:price_Measure_Unit.name", namespace).text,
                "curve_type": ts.find("ns:curveType", namespace).text,
                "periods": []
            }

            # Extract periods and points
            period = ts.find("ns:Period", namespace)
            if period:
                time_interval = period.find("ns:timeInterval", namespace)
                start = datetime.fromisoformat(time_interval.find("ns:start", namespace).text.replace("Z", "+00:00"))
                end = datetime.fromisoformat(time_interval.find("ns:end", namespace).text.replace("Z", "+00:00"))
                resolution = self.parse_duration(period.find("ns:resolution", namespace).text)

                points = []
                for point in period.findall("ns:Point", namespace):
                    position = int(point.find("ns:position", namespace).text)
                    price = float(point.find("ns:price.amount", namespace).text)
                    timestamp = start + (position - 1) * resolution
                    #utc_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S%z")
                    finnish_timezone = pytz.timezone("Europe/Helsinki")
                    # Convert UTC to Finnish time
                    finnish_time = timestamp.astimezone(finnish_timezone)
                    points.append({"timestamp": finnish_time.isoformat(), "price": price})

                ts_data["periods"].append({
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "resolution": str(resolution),
                    "points": points
                })

            time_series.append(ts_data)

        price_series = {}
        for ts in time_series:
            for period in ts["periods"]:
                for point in period["points"]:
                    price_series[point["timestamp"]] = round(point["price"]*100/1000, 2)
        #json_string = json.dumps(price_series, indent=4)
        return price_series


if __name__ == "__main__":
    ele_price = ElePrice()
    price_data = ele_price.get_price_info()
    dict_format = ele_price.format_price_to_dict(price_data)

    # Construct the file path
    file_path = os.path.join(os.path.dirname(__file__), "price_info.py")

    # Write to a temp file and atomically rename it into place so ele_api.py
    # never reads a partially-written price_info.py (os.replace is atomic
    # on POSIX, unlike writing file_path directly).
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w") as file:
        file.write(str(dict_format))
    os.replace(tmp_path, file_path)

    #print(json_format)
