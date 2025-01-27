from argparse import ArgumentParser
from astral import LocationInfo
from src.brightness_controller import BrightnessController
from src.location import get_coordinates, get_timezone_by_ip
import asyncio


async def main():
    default_min_brightness = 20
    default_max_brightness = 70
    default_change_speed = 1.0
    default_latitude = None
    default_longitude = None
    default_adaptive_brightness = False
    default_update_interval = 2.0

    parser = ArgumentParser()
    parser.add_argument("--min", type=int, default=default_min_brightness)
    parser.add_argument("--max", type=int, default=default_max_brightness)
    parser.add_argument("--speed", type=float, default=default_change_speed)
    parser.add_argument("--lat", type=float, default=default_latitude)
    parser.add_argument("--lng", type=float, default=default_longitude)
    parser.add_argument("--adapt", type=bool, default=default_adaptive_brightness)
    parser.add_argument("--interval", type=float, default=default_update_interval)
    args = parser.parse_args()

    min_brightness = args.min
    max_brightness = args.max
    change_speed = args.speed
    latitude = args.lat
    longitude = args.lng
    adaptive_brightness = args.adapt
    update_interval = args.interval

    if not (0 <= min_brightness <= 100):
        raise ValueError("Minimum brightness must be between 0 and 100.")
    if not (0 <= max_brightness <= 100):
        raise ValueError("Maximum brightness must be between 0 and 100.")
    if min_brightness >= max_brightness:
        raise ValueError("Minimum brightness must be less than maximum brightness.")
    controller = BrightnessController(
        min_brightness,
        max_brightness,
        change_speed,
        adaptive_brightness,
        update_interval,
    )

    if latitude is None or longitude is None:
        latitude, longitude = get_coordinates()
    timezone = get_timezone_by_ip()
    location = LocationInfo(timezone=timezone, latitude=latitude, longitude=longitude)

    await controller.start_main_loop(location)


asyncio.run(main())
