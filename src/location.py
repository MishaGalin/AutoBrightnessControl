from json import dump, load
from os import path
from requests import get, RequestException
from pytz import timezone
from timezonefinder import TimezoneFinder
from ctypes import windll


def save_coordinates_to_file(latitude: float, longitude: float, file_name: str) -> None:
    with open(file_name, "w") as file:
        dump({"latitude": latitude, "longitude": longitude}, file)


def load_coordinates_from_file(
    file_name: str,
) -> tuple[float | None, float | None]:
    if path.exists(file_name):
        with open(file_name, "r") as file:
            data = load(file)
            return data.get("latitude"), data.get("longitude")
    return None, None


def get_coordinates_by_ip() -> tuple[float | None, float | None]:
    try:
        response = get(url="https://ipinfo.io/json", timeout=10)
        response.raise_for_status()
        data = response.json()
        latitude, longitude = map(float, data["loc"].split(","))
        return latitude, longitude
    except (RequestException, ValueError):
        return None, None


def get_timezone(latitude: float, longitude: float) -> timezone:
    tf = TimezoneFinder()
    timezone_name = tf.certain_timezone_at(lng=longitude, lat=latitude)
    if timezone_name is None:
        raise ValueError("Can't find timezone by given coordinates.")
    return timezone(timezone_name)


def get_coordinates() -> tuple[float, float]:
    latitude, longitude = get_coordinates_by_ip()
    if (latitude is not None) and (longitude is not None):
        save_coordinates_to_file(latitude, longitude, "../coordinates.json")
    if (latitude is None) or (longitude is None):
        latitude, longitude = load_coordinates_from_file("coordinates.json")
    if (latitude is None) or (longitude is None):
        windll.user32.MessageBoxW(
            0,
            "Error: Unable to determine coordinates.\n\n"
            "Please check your internet connection or set coordinates manually using --lat and --lng.",
            "AutoBrightnessControl",
            0,
        )
        exit(1)
    return latitude, longitude
