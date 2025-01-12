from os import path
from json import dump, load
from requests import get, RequestException
from ctypes import windll
from argparse import ArgumentParser
from time import time
from sys import exit
from math import sin, pi, sqrt
from datetime import datetime, timedelta
from pytz import timezone
from astral.sun import sun
from astral import LocationInfo
from timezonefinder import TimezoneFinder
import dxcam
import numpy as np
import asyncio
import refreshrate
import screen_brightness_control as sbc

UPDATE_INTERVAL = 60  # Update interval in seconds
COORDINATES_FILE = "coordinates.json"  # File to store coordinates
LOG_FILE = "brightness_control_log.txt"
LOG = False
BASE_BRIGHTNESS = 0.0
ADJUSTED_BRIGHTNESS = 0.0


def log(message: str) -> None:
    if LOG:
        with open(LOG_FILE, "a") as file:
            file.write(message + "\n")

# noinspection PyTypeChecker
def save_coordinates_to_file(latitude: float,
                             longitude: float) -> None:
    try:
        with open(COORDINATES_FILE, "w") as file:
            dump({"latitude": latitude, "longitude": longitude},  file)
            file.close()
        log("Coordinates saved locally.")
    except Exception as e:
        log(f"Error saving coordinates: {e}")

def load_coordinates_from_file() -> tuple[float | None, float | None]:
    if path.exists(COORDINATES_FILE):
        try:
            with open(COORDINATES_FILE, "r") as file:
                data = load(file)
                file.close()
                return data.get("latitude"), data.get("longitude")
        except Exception as e:
            log(f"Error loading coordinates: {e}")
    return None, None

def get_coordinates_by_ip() -> tuple[float | None, float | None]:
    try:
        response = get("http://ipinfo.io/json", timeout=10)
        response.raise_for_status()  # Raise an exception if the request was unsuccessful
        data = response.json()
        if "loc" in data:
            latitude, longitude = map(float, data["loc"].split(","))
            return latitude, longitude
        else:
            raise ValueError("Location data not found in response.")
    except RequestException as e:
        log(f"Error fetching location data: {e}")
    except ValueError as e:
        log(f"Error parsing location data: {e}")

    return None, None

def get_coordinates() -> tuple[float, float]:
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
        windll.user32.MessageBoxW(0, "Error: Unable to determine coordinates. Exiting\nBut you can set them manually using arguments --lat and --lng", "Error", 0)
        exit(1)

    return latitude, longitude

def get_timezone_from_coordinates(latitude: float,
                                  longitude: float) -> timezone:
    tf = TimezoneFinder()
    timezone_name = tf.certain_timezone_at(lng=longitude, lat=latitude)
    if timezone_name is None:
        raise ValueError("Can't find timezone by given coordinates. ")
    return timezone(timezone_name)

def calculate_brightness(brightness_min: int,
                         brightness_max: int,
                         change_speed: float,
                         sunrise: datetime,
                         sunset: datetime,
                         current_time: datetime) -> float:
    """
    Calculates brightness based on current time and sunrise/sunset times.
    Brightness is maximum at midday and minimum at midnight.
    """

    day_duration = (sunset - sunrise).total_seconds()
    night_duration = (24 * 60 * 60) - day_duration
    brightness_range = brightness_max - brightness_min

    change_speed_day = change_speed
    change_speed_night = sqrt(change_speed_day * (day_duration / night_duration))

    if sunrise <= current_time <= sunset:  # Daytime phase
        progress = (current_time - sunrise).total_seconds() / day_duration
        brightness = brightness_min + brightness_range * (sin(pi * progress) ** change_speed_day + 1) / 2
    else:  # Nighttime phase
        if current_time > sunset:
            progress = (current_time - sunset).total_seconds() / night_duration
        else:
            progress = (current_time - sunset + timedelta(days=1)).total_seconds() / night_duration
        brightness = brightness_max - brightness_range * (sin(pi * progress) ** change_speed_night + 1) / 2

    return brightness

async def set_monitor_brightness_smoothly(start_brightness: int,
                                          end_brightness: int,
                                          animation_duration: float) -> None:

    #def ease_out_sine(x: float) -> float:
    #    return sin(x * pi / 2.0)

    if start_brightness == end_brightness:
        sbc.set_brightness(end_brightness)
        return

    frame_duration = 1.0 / refreshrate.get()
    last_value_current_brightness = start_brightness
    start_time = time()

    while True:
        start_time_animation_step = time()
        progress = (start_time_animation_step - start_time) / animation_duration
        current_brightness = round(start_brightness + progress * (end_brightness - start_brightness))

        # the end of the animation
        if progress >= 1.0 or current_brightness == end_brightness:
            sbc.set_brightness(end_brightness)
            break

        if current_brightness == last_value_current_brightness:
            end_time_animation_step = time()
            elapsed_time_animation_step = end_time_animation_step - start_time_animation_step
            await asyncio.sleep(max(0.0, frame_duration - elapsed_time_animation_step))
            continue

        sbc.set_brightness(current_brightness)
        last_value_current_brightness = current_brightness

        end_time_animation_step = time()
        elapsed_time_animation_step = end_time_animation_step - start_time_animation_step
        #print(f"Fps: {(1.0 / elapsed_time_animation_step):.2f}\n")
        #print(f"Elapsed time animation step: {elapsed_time_animation_step:.3f}")
        #print(f"Sleeping for {frame_duration - elapsed_time_animation_step:.3f} seconds...")
        await asyncio.sleep(max(0.0, frame_duration - elapsed_time_animation_step))

#def plot_brightness_over_day(brightness_min: int,
#                                   brightness_max: int,
#                                   change_speed: float,
#                                   time_zone: timezone,
#                                   location: LocationInfo):
#
#    import matplotlib.pyplot as plt
#
#    times = []
#    brightness_values = []
#
#    current_time = datetime.now(time_zone)
#
#    s = sun(location.observer, date=current_time.date(), tzinfo=time_zone)
#    sunrise, sunset = s["sunrise"], s["sunset"]
#
#    step = 1
#    current_time = sunrise
#
#    while current_time < sunrise + timedelta(days=1):
#        brightness = calculate_brightness(sunrise, sunset, current_time, brightness_min, brightness_max, change_speed)
#        times.append(current_time)
#        brightness_values.append(brightness)
#        current_time += timedelta(minutes=step)
#
#    plt.figure(figsize=(10, 5))
#    plt.plot(times, brightness_values, label="Brightness", color='blue')
#    plt.xlabel("Time")
#    plt.ylabel("Brightness (%)")
#    plt.xticks(rotation=45)
#    plt.grid(True)
#    plt.tight_layout()
#    plt.show()


async def brightness_control(brightness_min: int,
                             brightness_max: int,
                             change_speed: float,
                             time_zone: timezone,
                             location: LocationInfo) -> None:

    """
    Main function that controls BASE_BRIGHTNESS based on current time and sunrise/sunset times.
    """

    while True:
        start_time = time()
        current_date = datetime.now(time_zone)

        s = sun(location.observer, date=current_date.date(), tzinfo=time_zone)
        sunrise, sunset = s["sunrise"], s["sunset"]

        global BASE_BRIGHTNESS
        BASE_BRIGHTNESS = calculate_brightness(brightness_min, brightness_max, change_speed, sunrise, sunset, current_date)

        log(f"Current time: {format(current_date, '%H:%M:%S')}, Sunrise: {format(sunrise, '%H:%M:%S')}, Sunset: {format(sunset, '%H:%M:%S')}")
        log(f"Base brightness: {BASE_BRIGHTNESS}%\n")

        end_time = time()
        elapsed_time = end_time - start_time
        await asyncio.sleep(max(0.0, UPDATE_INTERVAL - elapsed_time))

async def brightness_adjustment(brightness_min: int,
                                brightness_max: int,
                                update_interval: float) -> None:
    """
    Function that adjusts brightness based on content on the screen, if BRIGHTNESS_ADJ_ENABLED is True.
    """

    camera = dxcam.create()
    last_value_pixels = None
    brightness_addition_range = (brightness_max - brightness_min) / 2

    while True:
        start_time = time()
        screenshot = camera.grab()

        if screenshot is None:
            #print("No screenshot")
            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(0.0, update_interval - elapsed_time))
            continue

        aspect_ratio = screenshot.shape[1] / screenshot.shape[0]
        divider_y = round(screenshot.shape[0] / 60)
        divider_x = round(screenshot.shape[1] / (60 * aspect_ratio))

        pixels = screenshot[    divider_y : -divider_y : divider_y,
                                divider_x : -divider_x : divider_x] # take every pixel with a step of 'divider' except the edges

        if np.all(pixels == last_value_pixels):
            #print("Picture is the same")
            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(0.0, update_interval - elapsed_time))
            continue

        last_value_pixels = np.copy(pixels)

        max_by_subpixels = np.empty(shape=(pixels.shape[0], pixels.shape[1]), dtype=np.uint8)
        for i in range(max_by_subpixels.shape[0]):
            for j in range(max_by_subpixels.shape[1]):
                max_by_subpixels[i][j] = max(pixels[i][j])

        brightness_addition = float((np.mean(max_by_subpixels) / 255.0 - 0.5) * brightness_addition_range)  # 0 - 255   to   -(1/4 of brightness range) - (1/4 of brightness range)

        global BASE_BRIGHTNESS, ADJUSTED_BRIGHTNESS
        ADJUSTED_BRIGHTNESS = BASE_BRIGHTNESS + brightness_addition

        #print(f"Current base brightness: {BASE_BRIGHTNESS}%")
        #print(f"Adapted brightness: {adjusted_brightness}%\n")

        end_time = time()
        elapsed_time = end_time - start_time
        #print(f"Elapsed time: {elapsed_time:.3f} seconds")
        #print(f"Sleep time: {max((0, interval - elapsed_time)):.3f} seconds\n")

        await asyncio.sleep(max(0.0, update_interval - elapsed_time))

async def update_display_brightness(brightness_min: int,
                                    brightness_max: int,
                                    brightness_adj_enabled: bool,
                                    update_interval: float) -> None:
    """
    Continuously updates the brightness of the display.
    """

    last_value_current_brightness = sbc.get_brightness(display=0)[0]

    while True:
        start_time = time()

        if brightness_adj_enabled:
            global ADJUSTED_BRIGHTNESS
            current_brightness = ADJUSTED_BRIGHTNESS
        else:
            global BASE_BRIGHTNESS
            current_brightness = BASE_BRIGHTNESS

        current_brightness = round(current_brightness)
        current_brightness = max(brightness_min, min(brightness_max, current_brightness))

        if current_brightness != last_value_current_brightness:
            if abs(current_brightness - last_value_current_brightness) >= 5:
                await set_monitor_brightness_smoothly(last_value_current_brightness, current_brightness, 1.0)
            else:
                sbc.set_brightness(current_brightness)

            last_value_current_brightness = current_brightness

        end_time = time()
        elapsed_time = end_time - start_time
        #print(f"Elapsed time: {elapsed_time:.3f} seconds")
        await asyncio.sleep(max(0.0, update_interval - elapsed_time))


async def main():
    default_min_brightness          = 20
    default_max_brightness          = 70
    default_change_speed            = 1.0
    default_latitude                = None
    default_longitude               = None
    default_log                     = False
    default_brightness_adj_enabled  = False

    parser = ArgumentParser(description="Brightness control based on sunrise and sunset.")
    parser.add_argument("--min",    type=int,   default=default_min_brightness,         help=f"Minimum brightness (default: {default_min_brightness})")
    parser.add_argument("--max",    type=int,   default=default_max_brightness,         help=f"Maximum brightness (default: {default_max_brightness})")
    parser.add_argument("--speed",  type=float, default=default_change_speed,           help=f"Lower values make the transition around sunset and sunrise faster. Recommended value is from 0.5 to 1.0 (default: {default_change_speed})")
    parser.add_argument("--lat",    type=float, default=default_latitude,               help=f"Latitude (default: {'automatic detection' if default_latitude is None else default_latitude})")
    parser.add_argument("--lng",    type=float, default=default_longitude,              help=f"Longitude (default: {'automatic detection' if default_longitude is None else default_longitude})")
    parser.add_argument("--log",    type=bool,  default=default_log,                    help=f"Enable logging (default: {default_log})")
    parser.add_argument("--adj",    type=bool,  default=default_brightness_adj_enabled, help=f"Enable brightness adjustment (default: {default_brightness_adj_enabled})")
    args = parser.parse_args()

    brightness_min          = args.min
    brightness_max          = args.max
    change_speed            = args.speed
    latitude                = args.lat
    longitude               = args.lng
    brightness_adj_enabled  = args.adj

    global LOG
    LOG = args.log

    if latitude is None or longitude is None:
        latitude, longitude = get_coordinates()

    log(f"Brightness range: {brightness_min}% - {brightness_max}%")
    log(f"Coordinates: {latitude}, {longitude}")

    time_zone   = get_timezone_from_coordinates(latitude, longitude)
    location    = LocationInfo(timezone=time_zone.zone, latitude=latitude, longitude=longitude)
    update_interval = 2.0

    #plot_brightness_over_day(brightness_min, brightness_max, change_speed, time_zone, location)

    task_brightness_control = asyncio.create_task(
        brightness_control(brightness_min, brightness_max, change_speed, time_zone, location))

    if brightness_adj_enabled:
        task_brightness_adjustment = asyncio.create_task(
            brightness_adjustment(brightness_min, brightness_max, update_interval))

    task_update_display_brightness = asyncio.create_task(
        update_display_brightness(brightness_min, brightness_max, brightness_adj_enabled, update_interval))


    await task_brightness_control

    if brightness_adj_enabled:
        await task_brightness_adjustment

    await task_update_display_brightness


asyncio.run(main())
