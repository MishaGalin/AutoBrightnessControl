from argparse import ArgumentParser
from astral import LocationInfo
from src.brightness_controller import BrightnessController
from src.location import get_and_save_location_data
from ctypes import windll
import os
import psutil
import asyncio

PROCESS_NAME = "AutoBrightnessControl.exe"


def show_message_box(title: str, message: str) -> None:
    windll.user32.MessageBoxW(0, title, message, 0)


def kill_existing_instances():
    """
    Closes any existing instances of the program
    """
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] == PROCESS_NAME and proc.pid != os.getpid():
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass


async def main():
    kill_existing_instances()

    default_min_brightness = 20
    default_max_brightness = 70
    default_change_speed = 1.0
    default_latitude = None
    default_longitude = None
    default_adaptive = False
    default_primary_only = False
    default_interval = 2.0

    parser = ArgumentParser()
    parser.add_argument("--min", type=int, default=default_min_brightness)
    parser.add_argument("--max", type=int, default=default_max_brightness)
    parser.add_argument("--speed", type=float, default=default_change_speed)
    parser.add_argument("--lat", type=float, default=default_latitude)
    parser.add_argument("--lng", type=float, default=default_longitude)
    parser.add_argument("--adaptive", type=bool, default=default_adaptive)
    parser.add_argument("--primary-only", type=bool, default=default_primary_only)
    parser.add_argument("--interval", type=float, default=default_interval)
    args = parser.parse_args()

    min_brightness = args.min
    max_brightness = args.max
    change_speed = args.speed
    adaptive_brightness = args.adaptive
    primary_only = args.primary_only
    interval = args.interval

    try:
        if not (0 <= min_brightness <= 100):
            raise ValueError("Minimum brightness must be between 0 and 100")
        if not (0 <= max_brightness <= 100):
            raise ValueError("Maximum brightness must be between 0 and 100")
        if min_brightness >= max_brightness:
            raise ValueError("Minimum brightness must be less than maximum brightness")
        if interval <= 0:
            raise ValueError("Update interval must be greater than 0")
        latitude, longitude, time_zone = get_and_save_location_data()
        if args.lat is not None and args.lng is not None:
            latitude, longitude = args.lat, args.lng
        location = LocationInfo(
            latitude=latitude, longitude=longitude, timezone=time_zone
        )
        controller = BrightnessController(
            location,
            min_brightness,
            max_brightness,
            change_speed,
            adaptive_brightness,
            primary_only,
            interval,
        )
        await controller.start_main_loop()
    except Exception as e:
        show_message_box("Error: " + str(e), "AutoBrightnessControl")
        raise e


asyncio.run(main())
