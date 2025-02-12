from json import dump, load
from os import path
from requests import get, RequestException


def save_to_file(data: dict, file_name: str) -> None:
    with open(file_name, "w") as file:
        dump(data, file)


def load_from_file(file_name: str) -> dict:
    if path.exists(file_name):
        with open(file_name, "r") as file:
            return load(file)
    return {}


def get_location_data() -> dict:
    try:
        response = get(url="https://ipinfo.io/json", timeout=10)
        response.raise_for_status()
        data = response.json()
        latitude, longitude = map(float, data["loc"].split(","))
        time_zone = data["timezone"]
        return {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": time_zone,
        }
    except (RequestException, ValueError, KeyError):
        return {}


def get_and_save_location_data():
    """
    Returns latitude, longitude, timezone
    """
    file_name = "location_data.json"
    location_data = get_location_data()

    if location_data:
        save_to_file(location_data, file_name)
    else:
        location_data = load_from_file(file_name)
    if not location_data:
        raise RuntimeError("Unable to determine location data")
    return location_data.values()
