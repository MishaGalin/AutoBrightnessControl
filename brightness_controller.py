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
import refreshrate
import screen_brightness_control as sbc


class BrightnessController:
    def __init__(
        self,
        brightness_min: int,
        brightness_max: int,
        change_speed: float,
        brightness_adj_enabled: bool,
    ) -> None:
        self.min = brightness_min
        self.max = brightness_max
        self.change_speed = change_speed
        self.adj_enabled = brightness_adj_enabled
        self.base_brightness = 0.0
        self.adjusted_brightness = 0.0

    # noinspection PyTypeChecker
    @staticmethod
    def save_coordinates_to_file(
        latitude: float, longitude: float, file_name: str
    ) -> None:
        with open(file_name, "w") as file:
            dump({"latitude": latitude, "longitude": longitude}, file)
            file.close()

    @staticmethod
    def load_coordinates_from_file(
        file_name: str,
    ) -> tuple[float | None, float | None]:
        if path.exists(file_name):
            with open(file_name, "r") as file:
                data = load(file)
                file.close()
                return data.get("latitude"), data.get("longitude")
        return None, None

    @staticmethod
    def get_coordinates_by_ip() -> tuple[float | None, float | None]:
        try:
            response = get("https://ipinfo.io/json", timeout=10)
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
            BrightnessController.save_coordinates_to_file(latitude, longitude, "coordinates.json")

        if (latitude is None) or (longitude is None):
            latitude, longitude = BrightnessController.load_coordinates_from_file("coordinates.json")

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
        start_brightness: int, end_brightness: int, animation_duration: float
    ) -> None:

        if start_brightness == end_brightness:
            sbc.set_brightness(end_brightness)
            return

        frame_duration = 1.0 / refreshrate.get()
        last_brightness = start_brightness
        start_time = time()

        while True:
            start_time_animation_step = time()
            progress = (start_time_animation_step - start_time) / animation_duration
            current_brightness = round(
                start_brightness + progress * (end_brightness - start_brightness)
            )

            # the end of the animation
            if progress >= 1.0 or current_brightness == end_brightness:
                sbc.set_brightness(end_brightness)
                break

            if current_brightness != last_brightness:
                sbc.set_brightness(current_brightness)
                last_brightness = current_brightness

            end_time_animation_step = time()
            elapsed_time_animation_step = (
                end_time_animation_step - start_time_animation_step
            )
            await asyncio.sleep(max(0.0, frame_duration - elapsed_time_animation_step))

    async def start_brightness_control(
        self,
        time_zone: timezone,
        location: LocationInfo,
        update_interval: float,
    ) -> None:
        """
        Function that continuously controls brightness based on sunrise and sunset.
        """
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

    async def start_brightness_adjustment(self, update_interval: float) -> None:
        """
        Function that continuously adjusts brightness based on content on the screen.
        """

        camera = dxcam.create()
        brightness_addition_range = (self.max - self.min) / 2

        while True:
            start_time = time()
            screenshot = camera.grab()

            if screenshot is not None:
                pixel_density = 60
                divider = round(screenshot.shape[0] / pixel_density)

                # Get a sub-matrix of pixels with a step of 'divider' excluding the edges
                pixels = screenshot[divider::divider, divider::divider]

                max_by_subpixels = np.empty(
                    shape=(pixels.shape[0], pixels.shape[1]), dtype=np.uint8
                )

                for i in range(max_by_subpixels.shape[0]):
                    for j in range(max_by_subpixels.shape[1]):
                        max_by_subpixels[i][j] = max(pixels[i][j])

                brightness_addition = float(
                    (np.mean(max_by_subpixels) / 255.0 - 0.5)
                    * brightness_addition_range
                )
                # 0 - 255   to   (-1/4 of brightness range) - (1/4 of brightness range)

                self.adjusted_brightness = self.base_brightness + brightness_addition

            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(0.0, update_interval - elapsed_time))

    async def start_brightness_update(
        self,
        update_interval: float,
    ) -> None:
        """
        Function that continuously updates the brightness of the display.
        """
        last_brightness = sbc.get_brightness(display=0)[0]

        while True:
            start_time = time()

            if self.adj_enabled:
                current_brightness = round(self.adjusted_brightness)
            else:
                current_brightness = round(self.base_brightness)

            current_brightness = max(
                self.min,
                min(self.max, current_brightness),
            )

            if current_brightness != last_brightness:
                await self.set_brightness_smoothly(
                    last_brightness, current_brightness, 1.0
                )
                last_brightness = current_brightness

            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(0.0, update_interval - elapsed_time))
