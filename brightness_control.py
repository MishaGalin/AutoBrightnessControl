from argparse import ArgumentParser
from astral import LocationInfo
import asyncio
import brightness_controller as bc


async def main():
    default_min_brightness = 20
    default_max_brightness = 70
    default_change_speed = 1.0
    default_latitude = None
    default_longitude = None
    default_brightness_adj_enabled = False

    parser = ArgumentParser(
        description="Brightness control based on sunrise and sunset."
    )
    parser.add_argument(
        "--min",
        type=int,
        default=default_min_brightness,
        help=f"Minimum brightness (default: {default_min_brightness})",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=default_max_brightness,
        help=f"Maximum brightness (default: {default_max_brightness})",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=default_change_speed,
        help=f"Lower values make the transition around sunset and sunrise faster. Recommended value is from 0.5 to 1.0 (default: {default_change_speed})",
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=default_latitude,
        help=f"Latitude (default: {'automatic detection' if default_latitude is None else default_latitude})",
    )
    parser.add_argument(
        "--lng",
        type=float,
        default=default_longitude,
        help=f"Longitude (default: {'automatic detection' if default_longitude is None else default_longitude})",
    )
    parser.add_argument(
        "--adj",
        type=bool,
        default=default_brightness_adj_enabled,
        help=f"Enable brightness adjustment (default: {default_brightness_adj_enabled})",
    )
    args = parser.parse_args()

    brightness_min = args.min
    brightness_max = args.max
    change_speed = args.speed
    latitude = args.lat
    longitude = args.lng
    brightness_adj_enabled = args.adj

    if not (0 <= brightness_min <= 100):
        raise ValueError("Minimum brightness must be between 0 and 100.")
    if not (0 <= brightness_max <= 100):
        raise ValueError("Maximum brightness must be between 0 and 100.")
    if not (brightness_min < brightness_max):
        raise ValueError("Minimum brightness must be less than maximum brightness.")

    controller = bc.BrightnessController(
        brightness_min, brightness_max, change_speed, brightness_adj_enabled
    )

    if latitude is None or longitude is None:
        latitude, longitude = controller.get_coordinates()

    time_zone = controller.get_timezone(latitude, longitude)
    location = LocationInfo(
        timezone=time_zone.zone, latitude=latitude, longitude=longitude
    )

    task_brightness_control = asyncio.create_task(
        controller.start_brightness_control(
            time_zone,
            location,
            60.0,
        )
    )

    if brightness_adj_enabled:
        asyncio.create_task(controller.start_brightness_adjustment(2.0))

    asyncio.create_task(controller.start_brightness_update(2.0))

    await task_brightness_control


asyncio.run(main())
