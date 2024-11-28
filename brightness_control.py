import time
import matplotlib.pyplot as plt
from math import sin, pi
from datetime import datetime, timedelta
from pytz import timezone
from astral.sun import sun
from astral import LocationInfo
from monitorcontrol import get_monitors
from timezonefinder import TimezoneFinder

# Location parameters
CITY_NAME = "Ufa"
COUNTRY_NAME = "Russia"
LATITUDE = 54.738762  # Your coordinates
LONGITUDE = 55.972054
BRIGHTNESS_MIN = 0  # Minimum brightness (%)
BRIGHTNESS_MAX = 70  # Maximum brightness (%)
UPDATE_INTERVAL = 60  # Update interval in seconds

def get_timezone_from_coordinates(latitude, longitude):
    """Определяет временную зону по координатам."""
    tf = TimezoneFinder()
    timezone_name = tf.certain_timezone_at(lng=longitude, lat=latitude)
    if timezone_name is None:
        raise ValueError("Не удалось определить временную зону по указанным координатам.")
    return timezone(timezone_name)

def calculate_brightness(sunrise, sunset, current_time):
    """
    Calculates brightness based on current time and sunrise/sunset times.
    Brightness is maximum at midday and minimum at midnight.
    """
    day_duration = (sunset - sunrise).total_seconds()
    night_duration = (24 * 3600) - day_duration

    if sunrise <= current_time <= sunset:  # Daytime phase
        progress = (current_time - sunrise).total_seconds() / day_duration
        brightness = round(BRIGHTNESS_MIN + (BRIGHTNESS_MAX - BRIGHTNESS_MIN) * (sin(pi * (progress - 0.5) + pi/2) + 1) / 2)
    else:  # Night phase
        if current_time > sunset:
            progress = (current_time - sunset).total_seconds() / night_duration
        else:
            progress = (current_time - sunset + timedelta(days=1)).total_seconds() / night_duration
        brightness = round(BRIGHTNESS_MAX - (BRIGHTNESS_MAX - BRIGHTNESS_MIN) * (sin(pi * (progress - 0.5) + pi/2) + 1) / 2)

    return max(BRIGHTNESS_MIN, min(BRIGHTNESS_MAX, brightness))

def set_monitor_brightness(brightness, monitors):
    """Устанавливает яркость для мониторов."""
    for monitor in monitors:
        try:
            with monitor:
                if hasattr(monitor, 'set_luminance'):
                    monitor.set_luminance(brightness)
                else:
                    print(f"Монитор {monitor} не поддерживает управление яркостью.")
        except Exception as e:
            print(f"Ошибка установки яркости для монитора: {e}")

def plot_brightness_over_day(sunrise, sunset):
    """
    Plots the brightness change throughout the day.
    """
    times = []
    brightness_values = []

    # Split the day into intervals for display
    current_time = sunrise

    for _ in range(25):
        brightness = calculate_brightness(sunrise, sunset, current_time)
        times.append(current_time.strftime("%H:%M"))
        brightness_values.append(brightness)
        current_time += timedelta(hours=1)

    # Display the plot
    plt.figure(figsize=(10, 5))
    plt.plot(times, brightness_values, label="Brightness", color='blue')
    plt.xlabel("Time")
    plt.ylabel("Brightness (%)")
    plt.title(f"Brightness Change Throughout the Day ({CITY_NAME})")
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def main():
    # Определение временной зоны
    tz = get_timezone_from_coordinates(LATITUDE, LONGITUDE)
    location = LocationInfo(CITY_NAME, COUNTRY_NAME, tz.zone, LATITUDE, LONGITUDE)

    # Получение списка мониторов
    try:
        monitors = get_monitors()
        if not monitors:
            raise RuntimeError("Не удалось найти мониторы для управления яркостью.")
    except Exception as e:
        print(f"Ошибка получения списка мониторов: {e}")
        return

    while True:
        current_time = datetime.now(tz)

        # Get sunrise and sunset times with respect to the time zone
        s = sun(location.observer, date=current_time.date(), tzinfo=tz)
        sunrise, sunset = s["sunrise"], s["sunset"]

        # Calculate brightness
        brightness = calculate_brightness(sunrise, sunset, current_time)
        set_monitor_brightness(brightness, monitors)

        # Re-enable matplotlib import for debugging
        # Plot brightness for the entire day (only once)
        #plot_brightness_over_day(sunrise, sunset)

        #print(f"Current time: {current_time}")
        #print(f"Sunrise: {sunrise}")
        #print(f"Sunset: {sunset}")
        #print(f"Brightness: {brightness}%")

        # Pause until the next update
        time.sleep(UPDATE_INTERVAL)


if __name__ == "__main__":
    main()
