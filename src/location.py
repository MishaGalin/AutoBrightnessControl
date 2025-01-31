from json import dump, load
from os import path
from requests import get, RequestException
from pytz import timezone
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


def save_timezone_to_file(time_zone: timezone, file_name: str) -> None:
    with open(file_name, "w") as file:
        dump({"timezone": str(time_zone)}, file)


def load_timezone_from_file(file_name: str) -> timezone:
    if path.exists(file_name):
        with open(file_name, "r") as file:
            data = load(file)
            return timezone(data.get("timezone"))
    return None


def get_coordinates_by_ip() -> tuple[float | None, float | None]:
    try:
        response = get(url="https://ipinfo.io/json", timeout=10)
        response.raise_for_status()
        data = response.json()
        latitude, longitude = map(float, data["loc"].split(","))
        return latitude, longitude
    except (RequestException, ValueError):
        return None, None


def get_timezone_by_ip() -> timezone:
    try:
        response = get(url="https://ipinfo.io/json", timeout=10)
        response.raise_for_status()
        data = response.json()
        return timezone(data["timezone"])
    except (RequestException, ValueError):
        return None


def get_and_save_timezone() -> timezone:
    file_name = "timezone.json"
    time_zone = get_timezone_by_ip()
    if time_zone is not None:
        save_timezone_to_file(time_zone, file_name)
    if time_zone is None:
        time_zone = load_timezone_from_file(file_name)
    if time_zone is None:
        windll.user32.MessageBoxW(
            0,
            "Error: Unable to determine timezone.\n\n"
            "Please check your internet connection.",
            "AutoBrightnessControl",
            0,
        )
        raise RuntimeError("Unable to determine timezone")
    return time_zone


def get_and_save_coordinates() -> tuple[float, float]:
    file_name = "coordinates.json"
    latitude, longitude = get_coordinates_by_ip()
    if (latitude is not None) and (longitude is not None):
        save_coordinates_to_file(latitude, longitude, file_name)
    if (latitude is None) or (longitude is None):
        latitude, longitude = load_coordinates_from_file(file_name)
    if (latitude is None) or (longitude is None):
        windll.user32.MessageBoxW(
            0,
            "Error: Unable to determine coordinates.\n\n"
            "Please check your internet connection or set coordinates manually using --lat and --lng.",
            "AutoBrightnessControl",
            0,
        )
        raise RuntimeError("Unable to determine coordinates")
    return latitude, longitude
