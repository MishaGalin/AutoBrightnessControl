from argparse import ArgumentParser
from astral import LocationInfo
from src.brightness_controller import BrightnessController
from src.location import get_coordinates
import asyncio


async def main():
    default_min_brightness = 20
    default_max_brightness = 70
    default_change_speed = 1.0
    default_latitude = None
    default_longitude = None
    default_adaptive_brightness = False

    parser = ArgumentParser(
        description="Brightness control based on sunrise and sunset."
    )
    parser.add_argument("--min", type=int, default=default_min_brightness)
    parser.add_argument("--max", type=int, default=default_max_brightness)
    parser.add_argument("--speed", type=float, default=default_change_speed)
    parser.add_argument("--lat", type=float, default=default_latitude)
    parser.add_argument("--lng", type=float, default=default_longitude)
    parser.add_argument("--adapt", type=bool, default=default_adaptive_brightness)
    args = parser.parse_args()

    brightness_min = args.min
    brightness_max = args.max
    change_speed = args.speed
    latitude = args.lat
    longitude = args.lng
    adaptive_brightness = args.adapt

    if not (0 <= brightness_min <= 100):
        raise ValueError("Minimum brightness must be between 0 and 100.")
    if not (0 <= brightness_max <= 100):
        raise ValueError("Maximum brightness must be between 0 and 100.")
    if not (brightness_min < brightness_max):
        raise ValueError("Minimum brightness must be less than maximum brightness.")
    controller = BrightnessController(
        brightness_min, brightness_max, change_speed, adaptive_brightness
    )

    if latitude is None or longitude is None:
        latitude, longitude = get_coordinates()
    location = LocationInfo(latitude=latitude, longitude=longitude)

    await controller.start_main_loop(location, 2.0)


asyncio.run(main())
