from os import path
from json import dump, load
from requests import get, RequestException
from ctypes import windll
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
import screen_brightness_control as sbc


class BrightnessController:
    def __init__(
        self,
        brightness_min: int,
        brightness_max: int,
        change_speed: float,
        adaptive_brightness: bool,
    ) -> None:
        self.min = brightness_min
        self.max = brightness_max
        self.change_speed = change_speed
        self.adaptive_brightness = adaptive_brightness
        self.base_brightness = 0.0
        self.adapted_brightness = 0.0

    # noinspection PyTypeChecker

    @staticmethod
    def save_coordinates_to_file(
        latitude: float, longitude: float, file_name: str
    ) -> None:
        with open(file_name, "w") as file:
            dump({"latitude": latitude, "longitude": longitude}, file)

    @staticmethod
    def load_coordinates_from_file(
        file_name: str,
    ) -> tuple[float | None, float | None]:
        if path.exists(file_name):
            with open(file_name, "r") as file:
                data = load(file)
                return data.get("latitude"), data.get("longitude")
        return None, None

    @staticmethod
    def get_coordinates_by_ip() -> tuple[float | None, float | None]:
        try:
            response = get(url="https://ipinfo.io/json", timeout=10)
            response.raise_for_status()
            data = response.json()
            latitude, longitude = map(float, data["loc"].split(","))
            return latitude, longitude
        except (RequestException, ValueError):
            return None, None

    @staticmethod
    def get_timezone(latitude: float, longitude: float) -> timezone:
        tf = TimezoneFinder()
        timezone_name = tf.certain_timezone_at(lng=longitude, lat=latitude)
        if timezone_name is None:
            raise ValueError("Can't find timezone by given coordinates.")
        return timezone(timezone_name)

    @staticmethod
    def get_coordinates() -> tuple[float, float]:
        latitude, longitude = BrightnessController.get_coordinates_by_ip()
        if (latitude is not None) and (longitude is not None):
            BrightnessController.save_coordinates_to_file(
                latitude, longitude, "coordinates.json"
            )
        if (latitude is None) or (longitude is None):
            latitude, longitude = BrightnessController.load_coordinates_from_file(
                "coordinates.json"
            )
        if (latitude is None) or (longitude is None):
            windll.user32.MessageBoxW(
                0,
                "Error: Unable to determine coordinates.\n\n"
                "Please check your internet connection or set coordinates manually using --lat and --lng.",
                "Error",
                0,
            )
            exit(1)
        return latitude, longitude

    def calculate_base_brightness(
        self,
        sunrise: datetime,
        sunset: datetime,
        current_time: datetime,
    ) -> float:
        day_duration = (sunset - sunrise).total_seconds()
        night_duration = (24 * 60 * 60) - day_duration
        brightness_range = self.max - self.min

        change_speed_day = self.change_speed
        change_speed_night = sqrt(change_speed_day * (day_duration / night_duration))

        if sunrise <= current_time <= sunset:
            progress = (current_time - sunrise).total_seconds() / day_duration
            brightness = (
                self.min
                + brightness_range * (sin(pi * progress) ** change_speed_day + 1) / 2
            )
        else:
            if current_time > sunset:
                progress = (current_time - sunset).total_seconds() / night_duration
            else:
                progress = (
                    current_time - sunset + timedelta(days=1)
                ).total_seconds() / night_duration
            brightness = (
                self.max
                - brightness_range * (sin(pi * progress) ** change_speed_night + 1) / 2
            )
        return brightness

    @staticmethod
    async def set_brightness_smoothly(
        start_brightness: int,
        end_brightness: int,
        animation_duration: float,
        monitors: list[str],
    ) -> None:
        if start_brightness == end_brightness or animation_duration < 0.0001:
            sbc.set_brightness(end_brightness)
            return
        anim_step_duration = animation_duration / abs(end_brightness - start_brightness)
        last_brightness = start_brightness
        start_time = time() - anim_step_duration

        while True:
            anim_step_start_time = time()
            progress = (anim_step_start_time - start_time) / animation_duration
            current_brightness = round(
                start_brightness + progress * (end_brightness - start_brightness)
            )
            if progress >= 1.0 or current_brightness == end_brightness:
                sbc.set_brightness(end_brightness)
                break
            if current_brightness != last_brightness:
                for monitor in monitors:
                    sbc.set_brightness(current_brightness, display=monitor)
                last_brightness = current_brightness
            anim_step_end_time = time()
            anim_step_elapsed_time = anim_step_end_time - anim_step_start_time
            await asyncio.sleep(max(0.0, anim_step_duration - anim_step_elapsed_time))

    @staticmethod
    def get_supported_monitors(all_monitors: list[str]) -> list[str]:
        supported_monitors = []
        for monitor in all_monitors:
            try:
                sbc.get_brightness(display=monitor)
                supported_monitors.append(monitor)
            except sbc.exceptions.ScreenBrightnessError:
                continue
        if len(supported_monitors) == 0:
            windll.user32.MessageBoxW(
                0,
                "Error: Supported monitors not found",
                "Error",
                0,
            )
            exit(1)
        return supported_monitors.copy()

    async def start_brightness_control(
        self,
        location: LocationInfo,
        update_interval: float,
    ) -> None:
        """
        Continuously controls brightness based on sunrise and sunset.
        """
        time_zone = self.get_timezone(location.latitude, location.longitude)
        update_interval = max(0.0, update_interval)

        while True:
            start_time = time()
            current_time = datetime.now(time_zone)

            sun_data = sun(
                location.observer, date=current_time.date(), tzinfo=time_zone
            )
            sunrise, sunset = sun_data["sunrise"], sun_data["sunset"]

            self.base_brightness = self.calculate_base_brightness(
                sunrise,
                sunset,
                current_time,
            )

            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(0.0, update_interval - elapsed_time))

    async def start_brightness_adaptation(self, update_interval: float) -> None:
        """
        Continuously adapts brightness based on content on the screen.
        Ends immediately if adaptive brightness is disabled.
        """
        if not self.adaptive_brightness:
            return
        camera = dxcam.create()
        brightness_adaptation_range = (self.max - self.min) / 2
        update_interval = max(0.0, update_interval)

        while True:
            start_time = time()
            screenshot = camera.grab()

            if screenshot is not None:
                pixel_density = 60
                divider = round(screenshot.shape[0] / pixel_density)
                pixels = screenshot[divider::divider, divider::divider]
                # Get a sub-matrix of pixels with a step of 'divider' excluding the edges

                max_by_subpixels = np.empty(
                    shape=(pixels.shape[0], pixels.shape[1]), dtype=np.uint8
                )

                for i in range(max_by_subpixels.shape[0]):
                    for j in range(max_by_subpixels.shape[1]):
                        max_by_subpixels[i][j] = max(pixels[i][j])
                brightness_addition = float(
                    (np.mean(max_by_subpixels) / 255.0 - 0.5)
                    * brightness_adaptation_range
                )
                # 0 - 255   to   (-1/4 of brightness range) - (1/4 of brightness range)

                self.adapted_brightness = self.base_brightness + brightness_addition
            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(0.0, update_interval - elapsed_time))

    async def start_brightness_update(
        self,
        update_interval: float,
    ) -> None:
        """
        Continuously updates the brightness of the display.
        """
        update_interval = max(0.0, update_interval)
        last_brightness = 0
        supported_monitors = []
        last_all_monitors = []

        while True:
            start_time = time()

            # Update the list of monitors and select those that support brightness adjustment

            all_monitors = sbc.list_monitors()
            if all_monitors != last_all_monitors:
                supported_monitors = self.get_supported_monitors(all_monitors)
                last_brightness = sbc.get_brightness(display=supported_monitors[0])[0]
                last_all_monitors = all_monitors
            if self.adaptive_brightness:
                current_brightness = round(self.adapted_brightness)
            else:
                current_brightness = round(self.base_brightness)
            current_brightness = max(
                self.min,
                min(self.max, current_brightness),
            )

            if current_brightness != last_brightness:
                await self.set_brightness_smoothly(
                    last_brightness, current_brightness, 1.0, supported_monitors
                )
                last_brightness = current_brightness
            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(0.0, update_interval - elapsed_time))

    async def start_main_loop(
        self, location: LocationInfo, update_interval: float
    ) -> None:
        """
        Starts the main loop of the brightness controller.
        """
        tasks = [
            asyncio.create_task(
                self.start_brightness_control(location, update_interval)
            ),
            asyncio.create_task(self.start_brightness_adaptation(update_interval)),
            asyncio.create_task(self.start_brightness_update(update_interval)),
        ]
        await asyncio.gather(*tasks)
