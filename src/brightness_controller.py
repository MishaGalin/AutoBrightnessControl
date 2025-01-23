from ctypes import windll
from time import time
from sys import exit
from math import sin, pi, sqrt
from datetime import datetime, timedelta
from astral.sun import sun
from astral import LocationInfo
from src.location import get_timezone
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
        update_interval: float,
    ) -> None:
        self._min = brightness_min
        self._max = brightness_max
        self.change_speed = change_speed
        self._is_adaptive = adaptive_brightness
        self._interval = update_interval
        self._base_brightness = 0.0
        self._adapted_brightness = 0.0
        self._task_queue = [
            "control",
            "adaptation",
            "update",
        ]
        self._current_task = 0
        self._all_monitors = []
        self._supported_monitors = []

        self.update_monitor_list()
        if not self._is_adaptive:
            self._task_queue.remove("adaptation")

    @property
    def min(self):
        return self._min

    @min.setter
    def min(self, value: int):
        if value < 0 or value > 100:
            raise ValueError("min must be between 0 and 100")
        if value > self._max:
            raise ValueError("min must be less than max")
        self._min = value

    @property
    def max(self):
        return self._max

    @max.setter
    def max(self, value: int):
        if value < 0 or value > 100:
            raise ValueError("max must be between 0 and 100")
        if value < self._min:
            raise ValueError("max must be greater than min")
        self._max = value

    @property
    def is_adaptive(self):
        return self._is_adaptive

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, value: float):
        if value < 0:
            raise ValueError("interval must be greater than 0")
        self._interval = value

    @property
    def base_brightness(self):
        return self._base_brightness

    @property
    def adapted_brightness(self):
        return self._adapted_brightness

    @property
    def task_queue(self):
        return self._task_queue

    @property
    def current_task(self):
        return self._current_task

    @property
    def all_monitors(self):
        return self._all_monitors

    @property
    def supported_monitors(self):
        return self._supported_monitors

    async def set_brightness_smoothly(
        self,
        start_brightness: int,
        end_brightness: int,
        animation_duration: float,
        monitors: list[str] = None,
    ) -> None:
        if start_brightness == end_brightness or animation_duration < 0.001:
            sbc.set_brightness(end_brightness)
            return
        if monitors is None:
            monitors = self._supported_monitors
        anim_step_duration = animation_duration / abs(end_brightness - start_brightness)
        last_brightness = start_brightness
        start_time = time() - anim_step_duration

        while True:
            anim_step_start_time = time()
            if self.update_monitor_list():
                return
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
    def get_supported_monitors(monitors: list[str] = None) -> list[str]:
        supported_monitors = []
        if monitors is None:
            monitors = sbc.list_monitors()
        for monitor in monitors:
            try:
                sbc.get_brightness(display=monitor)
                supported_monitors.append(monitor)
            except sbc.exceptions.ScreenBrightnessError:
                continue
        return supported_monitors

    def update_monitor_list(self) -> bool:
        """
        Updates the lists of all monitors and supported monitors.
        Returns True if the list of all monitors has changed.
        """
        new_all_monitors = sbc.list_monitors()
        if self._all_monitors != new_all_monitors:
            self._all_monitors = new_all_monitors
            self._supported_monitors = self.get_supported_monitors(self._all_monitors)
            if len(self._supported_monitors) == 0:
                windll.user32.MessageBoxW(
                    0,
                    "Error: Supported monitors not found",
                    "AutoBrightnessControl",
                    0,
                )
                exit(1)
            return True
        return False

    def calculate_base_brightness(
        self,
        sunrise: datetime,
        sunset: datetime,
        current_time: datetime,
    ) -> float:
        day_duration = (sunset - sunrise).total_seconds()
        night_duration = (24 * 60 * 60) - day_duration
        brightness_range = self._max - self._min

        change_speed_day = self.change_speed
        change_speed_night = sqrt(change_speed_day * (day_duration / night_duration))

        if sunrise <= current_time <= sunset:
            progress = (current_time - sunrise).total_seconds() / day_duration
            brightness = (
                self._min
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
                self._max
                - brightness_range * (sin(pi * progress) ** change_speed_night + 1) / 2
            )
        return brightness

    async def brightness_control_task(
        self,
        location: LocationInfo,
    ) -> None:
        """
        Continuously controls brightness based on sunrise and sunset.
        """
        time_zone = get_timezone(location.latitude, location.longitude)

        while True:
            start_time = time()
            if self._task_queue[self._current_task] != "control":
                await asyncio.sleep(self._interval / 4)
                continue
            current_time = datetime.now(time_zone)

            sun_data = sun(
                location.observer, date=current_time.date(), tzinfo=time_zone
            )
            sunrise, sunset = sun_data["sunrise"], sun_data["sunset"]

            self._base_brightness = self.calculate_base_brightness(
                sunrise,
                sunset,
                current_time,
            )

            self._current_task = (self._current_task + 1) % len(self._task_queue)
            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(self._interval / 4, self._interval - elapsed_time))

    async def brightness_adaptation_task(self) -> None:
        """
        Continuously adapts brightness based on content on the screen.
        """
        camera = dxcam.create()
        brightness_adaptation_range = (self._max - self._min) / 2

        while True:
            start_time = time()
            if self._task_queue[self._current_task] != "adaptation":
                await asyncio.sleep(self._interval / 4)
                continue
            if self.update_monitor_list():
                del camera
                camera = dxcam.create()
            screenshot = camera.grab()

            if screenshot is not None:
                pixel_density = 60
                divider = round(screenshot.shape[0] / pixel_density)
                pixels = screenshot[divider:-divider:divider, divider:-divider:divider]
                # Get a sub-matrix of pixels with a step of 'divider' excluding the edges

                max_by_subpixels = np.empty(
                    shape=(pixels.shape[0], pixels.shape[1]), dtype=np.uint8
                )

                for i in range(max_by_subpixels.shape[0]):
                    for j in range(max_by_subpixels.shape[1]):
                        max_by_subpixels[i][j] = max(pixels[i][j])
                brightness_addition = (
                    np.mean(max_by_subpixels) / 255.0 - 0.5
                ) * brightness_adaptation_range
                # 0 - 255   to   (-1/4 of brightness range) - (1/4 of brightness range)

                self._adapted_brightness = self._base_brightness + brightness_addition
            self._current_task = (self._current_task + 1) % len(self._task_queue)
            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(self._interval / 4, self._interval - elapsed_time))

    async def brightness_update_task(
        self,
    ) -> None:
        """
        Continuously updates the brightness of the display.
        """
        last_brightness = sbc.get_brightness(display=self._supported_monitors[0])[0]
        while True:
            start_time = time()
            if self._task_queue[self._current_task] != "update":
                await asyncio.sleep(self._interval / 4)
                continue
            if self.update_monitor_list():
                last_brightness = sbc.get_brightness(
                    display=self._supported_monitors[0]
                )[0]
            if self._is_adaptive:
                current_brightness = round(self._adapted_brightness)
            else:
                current_brightness = round(self._base_brightness)
            current_brightness = max(
                self._min,
                min(self._max, current_brightness),
            )

            if current_brightness != last_brightness:
                await self.set_brightness_smoothly(
                    last_brightness,
                    current_brightness,
                    self._interval / 2,
                )
                last_brightness = current_brightness
            self._current_task = (self._current_task + 1) % len(self._task_queue)
            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(self._interval / 4, self._interval - elapsed_time))

    async def start_main_loop(self, location: LocationInfo) -> None:
        """
        Starts the main loop of the brightness controller.
        """
        async with asyncio.TaskGroup() as tg:
            for task in self._task_queue:
                if task == "control":
                    tg.create_task(self.brightness_control_task(location))
                elif task == "adaptation":
                    tg.create_task(self.brightness_adaptation_task())
                elif task == "update":
                    tg.create_task(self.brightness_update_task())
