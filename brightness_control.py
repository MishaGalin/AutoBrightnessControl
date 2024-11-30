import sys
import time
import os
import json
import requests
import ctypes
import argparse
from math import sin, pi
from datetime import datetime, timedelta
from pytz import timezone
from astral.sun import sun
from astral import LocationInfo
from monitorcontrol import get_monitors
from timezonefinder import TimezoneFinder

UPDATE_INTERVAL = 60  # Update interval in seconds
COORDINATES_FILE = "coordinates.json"  # File to store coordinates
LOG_FILE = "brightness_control.txt"
LOG = False  # Set to True to enable logging

def log(message):
    if LOG:
        with open(LOG_FILE, "a") as file:
            file.write(message + "\n")

def save_coordinates_to_file(latitude, longitude):
    try:
        with open(COORDINATES_FILE, "w") as file:
            json.dump({"latitude": latitude, "longitude": longitude},  file)
        log("Coordinates saved locally.")
    except Exception as e:
        log(f"Error saving coordinates: {e}")

def load_coordinates_from_file():
    if os.path.exists(COORDINATES_FILE):
        try:
            with open(COORDINATES_FILE, "r") as file:
                data = json.load(file)
                return data.get("latitude"), data.get("longitude")
        except Exception as e:
            log(f"Error loading coordinates: {e}")
    return None, None

def get_coordinates_by_ip():
    try:
        response = requests.get("http://ipinfo.io/json", timeout=10)
        response.raise_for_status()  # Raise an exception if the request was unsuccessful
        data = response.json()
        if "loc" in data:
            latitude, longitude = map(float, data["loc"].split(","))
            return latitude, longitude
        else:
            raise ValueError("Location data not found in response.")
    except requests.RequestException as e:
        log(f"Error fetching location data: {e}")
    except ValueError as e:
        log(f"Error parsing location data: {e}")

    return None, None

def get_coordinates():
    latitude, longitude = None, None

    # Try to fetch coordinates online
    try:
        latitude, longitude = get_coordinates_by_ip()
        if (latitude is not None) and (longitude is not None):
            save_coordinates_to_file(latitude, longitude)
    except Exception as e:
        log(f"Error fetching coordinates online: {e}")

    # If coordinates are still None, try to load them from local file
    if (latitude is None) or (longitude is None):
        log("Attempting to load coordinates from local file...")
        latitude, longitude = load_coordinates_from_file()

    # If coordinates are still None, exit
    if (latitude is None) or (longitude is None):
        log("Error: Unable to determine coordinates. Exiting.")
        ctypes.windll.user32.MessageBoxW(0, "Error: Unable to determine coordinates. Exiting\nBut you can set them manually in the code :)", "Error", 0)
        sys.exit(1)

    return latitude, longitude

def get_timezone_from_coordinates(latitude, longitude):
    tf = TimezoneFinder()
    timezone_name = tf.certain_timezone_at(lng=longitude, lat=latitude)
    if timezone_name is None:
        raise ValueError("Can't find timezone by given coordinates. ")
    return timezone(timezone_name)

def calculate_brightness(sunrise, sunset, current_time, brightness_min, brightness_max):
    """
    Calculates brightness based on current time and sunrise/sunset times.
    Brightness is maximum at midday and minimum at midnight.
    """
    day_duration = (sunset - sunrise).total_seconds()
    night_duration = (24 * 3600) - day_duration

    if sunrise <= current_time <= sunset:  # Daytime phase
        progress = (current_time - sunrise).total_seconds() / day_duration
        brightness = round(brightness_min + (brightness_max - brightness_min) * (sin(pi * (progress - 0.5) + pi/2) + 1) / 2)
    else:  # Night phase
        if current_time > sunset:
            progress = (current_time - sunset).total_seconds() / night_duration
        else:
            progress = (current_time - sunset + timedelta(days=1)).total_seconds() / night_duration
        brightness = round(brightness_max - (brightness_max - brightness_min) * (sin(pi * (progress - 0.5) + pi/2) + 1) / 2)

    return max(brightness_min, min(brightness_max, brightness))

def set_monitor_brightness(brightness, monitors):
    for monitor in monitors:
        try:
            with monitor:
                if hasattr(monitor, 'set_luminance'):
                    monitor.set_luminance(brightness)
                else:
                    log(f"The {monitor} monitor does not support brightness control.")
        except Exception as e:
                log(f" Error setting brightness: {e}")

def main():
    default_min_brightness = 20
    default_max_brightness = 70

    parser = argparse.ArgumentParser(description="Brightness control based on sunrise and sunset.")
    parser.add_argument("--min", type=int, default=default_min_brightness, help=f"Minimum brightness (default: {default_min_brightness})")
    parser.add_argument("--max", type=int, default=default_max_brightness, help=f"Maximum brightness (default: {default_max_brightness})")
    parser.add_argument("--lat", type=float, default=None, help="Latitude")
    parser.add_argument("--lng", type=float, default=None, help="Longitude")
    args = parser.parse_args()

    brightness_min = args.min
    brightness_max = args.max

    log(f"Brightness range set: {brightness_min}% - {brightness_max}%")

    if (args.lat is not None) and (args.lng is not None):
        latitude, longitude = args.lat, args.lng
    else:
        latitude, longitude = get_coordinates()

    tz = get_timezone_from_coordinates(latitude, longitude)
    location = LocationInfo(timezone=tz.zone, latitude=latitude, longitude=longitude)

    log(f"Coordinates: {latitude}, {longitude}")

    try:
        monitors = get_monitors()
        if not monitors:
            raise RuntimeError("No monitors found.")
    except Exception as e:
        log(f"Error getting monitors: {e}")
        return

    while True:
        current_time = datetime.now(tz)

        s = sun(location.observer, date=current_time.date(), tzinfo=tz)
        sunrise, sunset = s["sunrise"], s["sunset"]

        brightness = calculate_brightness(sunrise, sunset, current_time, brightness_min, brightness_max)
        set_monitor_brightness(brightness, monitors)

        log(f"Current time: {current_time}, Sunrise: {sunrise}, Sunset: {sunset}, Brightness: {brightness}")

        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
