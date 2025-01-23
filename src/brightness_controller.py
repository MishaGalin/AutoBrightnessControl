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
        self.min = brightness_min
        self.max = brightness_max
        self.change_speed = change_speed
        self.adaptive_brightness = adaptive_brightness
        self.interval = max(1 / 60, update_interval)
        self.base_brightness = 0.0
        self.adapted_brightness = 0.0
        self.task_queue = [
            "control",
            "adaptation",
            "update",
        ]
        self.current_task = 0
        self.all_monitors = []
        self.supported_monitors = []
        self.update_monitor_list()

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
            monitors = self.supported_monitors
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
        if len(supported_monitors) == 0:
            windll.user32.MessageBoxW(
                0,
                "Error: Supported monitors not found",
                "AutoBrightnessControl",
                0,
            )
            exit(1)
        return supported_monitors

    def update_monitor_list(self) -> bool:
        """
        Updates the lists of all monitors and supported monitors.
        Returns True if the list of all monitors has changed.
        """
        new_all_monitors = sbc.list_monitors()
        if self.all_monitors != new_all_monitors:
            self.all_monitors = new_all_monitors
            self.supported_monitors = self.get_supported_monitors(self.all_monitors)
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

    async def brightness_control_task(
        self,
        location: LocationInfo,
    ) -> None:
        """
        Continuously controls brightness based on sunrise and sunset.
        """
        time_zone = get_timezone(location.latitude, location.longitude)

        while True:
            if self.task_queue[self.current_task] != "control":
                await asyncio.sleep(self.interval / 4)
                continue
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

            self.current_task = (self.current_task + 1) % len(self.task_queue)
            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(self.interval / 4, self.interval - elapsed_time))

    async def brightness_adaptation_task(self) -> None:
        """
        Continuously adapts brightness based on content on the screen.
        """
        camera = dxcam.create()
        brightness_adaptation_range = (self.max - self.min) / 2

        while True:
            if self.task_queue[self.current_task] != "adaptation":
                await asyncio.sleep(self.interval / 4)
                continue
            start_time = time()
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

                self.adapted_brightness = self.base_brightness + brightness_addition
            self.current_task = (self.current_task + 1) % len(self.task_queue)
            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(self.interval / 4, self.interval - elapsed_time))

    async def brightness_update_task(
        self,
    ) -> None:
        """
        Continuously updates the brightness of the display.
        """
        last_brightness = sbc.get_brightness(display=self.supported_monitors[0])[0]
        while True:
            if self.task_queue[self.current_task] != "update":
                await asyncio.sleep(self.interval / 4)
                continue
            start_time = time()
            if self.update_monitor_list():
                last_brightness = sbc.get_brightness(
                    display=self.supported_monitors[0]
                )[0]
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
                    last_brightness,
                    current_brightness,
                    self.interval / 2,
                )
                last_brightness = current_brightness
            self.current_task = (self.current_task + 1) % len(self.task_queue)
            end_time = time()
            elapsed_time = end_time - start_time
            await asyncio.sleep(max(self.interval / 4, self.interval - elapsed_time))

    async def start_main_loop(self, location: LocationInfo) -> None:
        """
        Starts the main loop of the brightness controller.
        """
        tasks = []

        if not self.adaptive_brightness:
            self.task_queue.remove("adaptation")
        async with asyncio.TaskGroup() as tg:
            for task in self.task_queue:
                if task == "control":
                    tasks.append(tg.create_task(self.brightness_control_task(location)))
                elif task == "adaptation":
                    tasks.append(tg.create_task(self.brightness_adaptation_task()))
                elif task == "update":
                    tasks.append(tg.create_task(self.brightness_update_task()))
