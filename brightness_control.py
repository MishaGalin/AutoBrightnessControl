from os import path
from json import dump, load
from requests import get, RequestException
from ctypes import Structure, windll, c_uint, sizeof, byref
from argparse import ArgumentParser
from time import sleep, time
from sys import exit
from math import sin, pi, sqrt
from datetime import datetime, timedelta
from pytz import timezone
from astral.sun import sun
from astral import LocationInfo
from timezonefinder import TimezoneFinder
import d3dshot
import numpy as np
import asyncio
import refreshrate
import screen_brightness_control as sbc

UPDATE_INTERVAL = 60  # Update interval in seconds
COORDINATES_FILE = "coordinates.json"  # File to store coordinates
LOG_FILE = "brightness_control_log.txt"

lock = asyncio.Lock()

BASE_BRIGHTNESS = 50

def log(message: str) -> None:
    if LOG:
        with open(LOG_FILE, "a") as file:
            file.write(message + "\n")

def save_coordinates_to_file(latitude: float,
                             longitude: float) -> None:
    try:
        with open(COORDINATES_FILE, "w") as file:
            dump({"latitude": latitude, "longitude": longitude},  file)
            file.close()
        log("Coordinates saved locally.")
    except Exception as e:
        log(f"Error saving coordinates: {e}")

def load_coordinates_from_file() -> tuple[float, float]:
    if path.exists(COORDINATES_FILE):
        try:
            with open(COORDINATES_FILE, "r") as file:
                data = load(file)
                file.close()
                return data.get("latitude"), data.get("longitude")
        except Exception as e:
            log(f"Error loading coordinates: {e}")
    return None, None

def get_coordinates_by_ip() -> tuple[float, float]:
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
        windll.user32.MessageBoxW(0, "Error: Unable to determine coordinates. Exiting\nBut you can set them manually in the code :)", "Error", 0)
        exit(1)

    return latitude, longitude

def get_timezone_from_coordinates(latitude: float,
                                  longitude: float) -> timezone:
    tf = TimezoneFinder()
    timezone_name = tf.certain_timezone_at(lng=longitude, lat=latitude)
    if timezone_name is None:
        raise ValueError("Can't find timezone by given coordinates. ")
    return timezone(timezone_name)

def calculate_brightness(sunrise: datetime,
                         sunset: datetime,
                         current_time: datetime,
                         brightness_min: int,
                         brightness_max: int,
                         change_speed: float) -> int:
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
        brightness = round(brightness_min + brightness_range * (sin(pi * progress) ** change_speed_day + 1) / 2)
    else:  # Nighttime phase
        if current_time > sunset:
            progress = (current_time - sunset).total_seconds() / night_duration
        else:
            progress = (current_time - sunset + timedelta(days=1)).total_seconds() / night_duration
        brightness = round(brightness_max - brightness_range * (sin(pi * progress) ** change_speed_night + 1) / 2)

    return brightness

def set_monitor_brightness(brightness: int,
                           monitors: list) -> None:
    for monitor in monitors:
        sbc.set_brightness(brightness, display=monitor)

#def set_monitor_brightness_smoothly(brightness: int,
#                                    monitors: list,
#                                    animation_duration: float) -> None:
#    def ease_out_sine(x: float) -> float:
#        return sin(x * pi / 2.0)
#
#    refresh_rate = min(120, refreshrate.get())
#    frame_duration = 1.0 / refresh_rate
#
#    start_time = time()
#    start_luminance = {}
#    end_luminance = brightness
#
#    # Получаем начальную яркость каждого монитора
#    for monitor in monitors:
#        try:
#            with monitor:
#                start_luminance[monitor] = monitor.get_luminance()
#        except Exception as e:
#            log(f" Error getting brightness: {e}")
#
#    # Параллельное выполнение анимации для каждого монитора
#    def update_monitor_brightness(monitor, start_luminance, progress):
#        with monitor:
#            current_luminance = round(ease_out_sine(progress) * (end_luminance - start_luminance) + start_luminance)
#            monitor.set_luminance(current_luminance)
#
#    # Основной цикл анимации
#    while True:
#        start_time_animation_step = time()
#        progress = (time() - start_time) / animation_duration
#
#        if progress >= 1.0:
#            break
#
#        # Параллельно обновляем яркость каждого монитора
#        threads = []
#        for monitor in monitors:
#            thread = threading.Thread(target=update_monitor_brightness, args=(monitor, start_luminance[monitor], progress))
#            threads.append(thread)
#            thread.start()
#
#        # Ждем завершения всех потоков
#        for thread in threads:
#            thread.join()
#
#        # Ограничиваем частоту кадров
#        end_time_animation_step = time()
#        elapsed_time_animation_step = end_time_animation_step - start_time_animation_step
#        print(f"Fps: {(1 / elapsed_time_animation_step):.2f}")
#        print(f"Elapsed time animation step: {elapsed_time_animation_step:.3f}")
#        print(f"Sleeping for {frame_duration - elapsed_time_animation_step:.3f} seconds...")
#        sleep(np.max((0, frame_duration - elapsed_time_animation_step)))
#
#        # Обновляем время для следующего шага
#        start_time = time()
#
#    # Финальная установка яркости
#    for monitor in monitors:
#        try:
#            with monitor:
#                if hasattr(monitor, 'set_luminance'):
#                    monitor.set_luminance(end_luminance)
#                else:
#                    log(f"The {monitor} monitor does not support brightness control.")
#        except Exception as e:
#                log(f" Error setting brightness: {e}")

def set_monitor_brightness_smoothly(brightness: int,
                                    monitors: list,
                                    animation_duration: float) -> None:

    def ease_out_sine(x: float) -> float:
        return np.sin(x * pi / 2.0)

    start_time = time()
    refresh_rate = min(120, refreshrate.get())
    frame_duration = 1.0 / refresh_rate

    start_luminance = {}
    current_luminance = None
    end_luminance = brightness

    # Get the initial brightness of each monitor
    for monitor in monitors:
        start_luminance[monitor] = sbc.get_brightness(display=monitor)[0]

    # Set the brightness of each monitor smoothly
    while True:
        start_time_animation_step = time()
        progress = (time() - start_time) / animation_duration

        if progress >= 1.0:
            break

        for monitor in monitors:
            current_luminance = round(ease_out_sine(progress) * (end_luminance - start_luminance[monitor]) + start_luminance[monitor])
            sbc.set_brightness(current_luminance, display=monitor)

        if current_luminance == end_luminance:
            break

        end_time_animation_step = time()
        elapsed_time_animation_step = end_time_animation_step - start_time_animation_step
        #print(f"Fps: {(1 / elapsed_time_animation_step):.2f}")
        #print(f"Elapsed time animation step: {elapsed_time_animation_step:.3f}")
        #print(f"Sleeping for {frame_duration - elapsed_time_animation_step:.3f} seconds...")
        sleep(np.max((0, frame_duration - elapsed_time_animation_step)))

    # Set the final brightness of each monitor
    for monitor in monitors:
        sbc.set_brightness(end_luminance, display=monitor)

#async def plot_brightness_over_day(time_zone, location, brightness_min, brightness_max, change_speed):
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
#    # Разбиваем день на интервалы для отображения
#    step = 1  # Разбиваем день на интервалы по минутам
#    current_time = sunrise
#
#    while current_time < sunrise + timedelta(days=1):
#        brightness = calculate_brightness(sunrise, sunset, current_time, brightness_min, brightness_max, change_speed)
#        times.append(current_time)
#        brightness_values.append(brightness)
#        current_time += timedelta(minutes=step)
#
#    # Отображаем график
#    plt.figure(figsize=(10, 5))
#    plt.plot(times, brightness_values, label="Brightness", color='blue')
#    plt.xlabel("Time")
#    plt.ylabel("Brightness (%)")
#    plt.xticks(rotation=45)
#    plt.grid(True)
#    plt.tight_layout()
#    plt.show()

def get_idle_duration():

    class LastInputInfo(Structure):
        _fields_ = [
            ('cbSize', c_uint),
            ('dwTime', c_uint),
        ]

    last_input_info = LastInputInfo()
    last_input_info.cbSize = sizeof(last_input_info)
    windll.user32.GetLastInputInfo(byref(last_input_info))
    millis = windll.kernel32.GetTickCount() - last_input_info.dwTime
    return millis / 1000.0

async def brightness_control(brightness_min: int,
                             brightness_max: int,
                             change_speed: float,
                             time_zone: timezone,
                             location: LocationInfo) -> None:

    while True:
        start_time = time()
        current_time = datetime.now(time_zone)

        s = sun(location.observer, date=current_time.date(), tzinfo=time_zone)
        sunrise, sunset = s["sunrise"], s["sunset"]

        async with lock:
            global BASE_BRIGHTNESS
            BASE_BRIGHTNESS = calculate_brightness(sunrise, sunset, current_time, brightness_min, brightness_max, change_speed)

        log(f"Current time: {format(current_time, '%H:%M:%S')}, Sunrise: {format(sunrise, '%H:%M:%S')}, Sunset: {format(sunset, '%H:%M:%S')}")
        log(f"Base brightness: {BASE_BRIGHTNESS}%\n")

        end_time = time()
        elapsed_time = end_time - start_time
        await asyncio.sleep(np.max((0, UPDATE_INTERVAL - elapsed_time)))

async def brightness_adjustment(brightness_min: int,
                                brightness_max: int,
                                monitors: list,
                                capture_agent: d3dshot.D3DShot) -> None:

    divider = 16
    last_value_adjusted_brightness = 0
    last_value_pixels = None

    while True:
        start_time = time()
        screenshot = capture_agent.screenshot()
#        if cp.cuda.is_available():
#            screenshot_gpu = cp.asarray(screenshot)
#
#            # Выбираем каждый второй пиксель по обеим осям (x и y)
#            screenshot_gpu_sampled = screenshot_gpu[::2, ::2]  # срезаем изображение с шагом 2
#
#            # Находим максимум для каждого пикселя (на GPU)
#            max_by_subpixels_gpu = cp.amax(screenshot_gpu_sampled, axis=-1)
#
#            # Переводим результат обратно на CPU (если нужно)
#            max_by_subpixels = cp.asnumpy(max_by_subpixels_gpu)
#
#            # Вычисляем среднее значение
#            mean_of_max_by_subpixels = np.mean(max_by_subpixels)

#        else:

        pixels = screenshot[  divider : -divider : divider,
                                        divider : -divider : divider] # take every pixel with a step of 'divider' except the edges

        # Check if the PC is idle and picture is the same
        if (np.all(pixels == last_value_pixels)) and get_idle_duration() > 5:
            #print("PC is idle")
            end_time = time()
            elapsed_time = end_time - start_time
            interval = 2.0
            await asyncio.sleep(np.max((0, interval - elapsed_time)))
            continue
        else:
            #print("PC is not idle")
            interval = 1.0
            last_value_pixels = pixels

        max_by_subpixels = np.zeros([pixels.shape[0], pixels.shape[1]])
        for i in range(max_by_subpixels.shape[0]):
            for j in range(max_by_subpixels.shape[1]):
                max_by_subpixels[i][j] = np.max(pixels[i][j])

        mean_of_max_by_subpixels = np.mean(max_by_subpixels)

        brightness_modifier = (mean_of_max_by_subpixels / 255.0) + 0.5  # 0 - 255 range to 0.5 - 1.5

        async with (lock):
            global BASE_BRIGHTNESS
            adjusted_brightness = round(BASE_BRIGHTNESS * brightness_modifier)

        adjusted_brightness = max(brightness_min, min(brightness_max, adjusted_brightness))

        if abs(adjusted_brightness - last_value_adjusted_brightness) > 5:
            set_monitor_brightness_smoothly(adjusted_brightness, monitors, interval)
        else:
            set_monitor_brightness(adjusted_brightness, monitors)

        last_value_adjusted_brightness = adjusted_brightness

        #print(f"Current base brightness: {BASE_BRIGHTNESS}%")
        #print(f"Adapted brightness: {adjusted_brightness}%\n")

        end_time = time()
        elapsed_time = end_time - start_time
        #print(f"Elapsed time: {elapsed_time:.3f} seconds")
        #print(f"Sleep time: {np.max((0, interval - elapsed_time)):.3f} seconds\n")

        await asyncio.sleep(np.max((0, interval - elapsed_time)))


async def main():
    default_min_brightness  = 20
    default_max_brightness  = 70
    default_change_speed    = 1.0
    default_latitude        = None
    default_longitude       = None
    default_log             = False
    #default_plot_flag       = False

    parser = ArgumentParser(description="Brightness control based on sunrise and sunset.")
    parser.add_argument("--min",    type=int,   default=default_min_brightness, help=f"Minimum brightness (default: {default_min_brightness})")
    parser.add_argument("--max",    type=int,   default=default_max_brightness, help=f"Maximum brightness (default: {default_max_brightness})")
    parser.add_argument("--speed",  type=float, default=default_change_speed,   help=f"Lower values make the transition around sunset and sunrise faster. Recommended value is from 0.5 to 1.0 (default: {default_change_speed})")
    parser.add_argument("--lat",    type=float, default=default_latitude,       help=f"Latitude (default: {'automatic detection' if default_latitude is None else default_latitude})")
    parser.add_argument("--lng",    type=float, default=default_longitude,      help=f"Longitude (default: {'automatic detection' if default_longitude is None else default_longitude})")
    parser.add_argument("--log",    action="store_true",                        help=f"Enable logging (default: {default_log})")
    #parser.add_argument("--plot",   action="store_true",                        help=f"Enable display of brightness graph (default: {default_log})")
    args = parser.parse_args()

    brightness_min  = args.min
    brightness_max  = args.max
    change_speed    = args.speed
    latitude        = args.lat
    longitude       = args.lng

    global LOG
    LOG = args.log

    if latitude is None or longitude is None:
        latitude, longitude = get_coordinates()

    #plot_flag = args.plot

    log(f"Brightness range: {brightness_min}% - {brightness_max}%")
    log(f"Coordinates: {latitude}, {longitude}")

    time_zone   = get_timezone_from_coordinates(latitude, longitude)
    location    = LocationInfo(timezone=time_zone.zone, latitude=latitude, longitude=longitude)

    monitors = sbc.list_monitors()

    #if plot_flag:
    #await plot_brightness_over_day(time_zone, location, brightness_min, brightness_max, change_speed)

    capture_agent = d3dshot.create(capture_output="numpy")

    task1 = asyncio.create_task(brightness_control(brightness_min, brightness_max, change_speed, time_zone, location))
    task2 = asyncio.create_task(brightness_adjustment(brightness_min, brightness_max, monitors, capture_agent))

    await task1
    await task2


asyncio.run(main())
