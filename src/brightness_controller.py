from ctypes import windll
from time import time
from math import sin, pi, sqrt
from datetime import datetime, timedelta
from astral.sun import sun
from astral import LocationInfo
import asyncio
import screen_brightness_control as sbc
from pytz import timezone


class BrightnessController:
    def __init__(
        self,
        min_brightness: int = 20,
        max_brightness: int = 70,
        change_speed: float = 1.0,
        adaptive_brightness: bool = False,
        update_interval: float = 2.0,
    ) -> None:
        self._min = min_brightness
        self._max = max_brightness
        self.change_speed = change_speed
        self._is_adaptive = adaptive_brightness
        self._interval = update_interval

        self._base_brightness = 0.0
        self._adapted_brightness = 0.0
        self._task_queue = [
            "monitor_list",
            "control",
            "adaptation",
            "update",
            "sleep",
        ]
        self._current_task = 0
        self._all_monitors = []
        self._supported_monitors = []
        self._monitor_list_updated = False
        self.paused = False
        self.__sum_elapsed_time = 0.0

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
        if value <= 0:
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

    @property
    def monitor_list_updated(self):
        return self._monitor_list_updated

    async def wait_for_task(self, task: str) -> None:
        if task not in self._task_queue:
            raise ValueError(f"Task {task} not found in task queue")
        while self._task_queue[self._current_task] != task:
            await asyncio.sleep(self._interval / 4)

    def switch_to_next_task(self) -> None:
        self._current_task = (self._current_task + 1) % len(self._task_queue)

    async def wait_for_unpause(self) -> None:
        while self.paused:
            await asyncio.sleep(1.0)

    def set_brightness(self, brightness: int, monitors: list[str] = None) -> None:
        if monitors is None:
            monitors = self._supported_monitors
        for monitor in monitors:
            sbc.set_brightness(brightness, display=monitor)

    async def set_brightness_smoothly(
        self,
        start_brightness: int,
        end_brightness: int,
        duration: float,
        monitors: list[str] = None,
    ) -> None:
        if monitors is None:
            monitors = self._supported_monitors
        if start_brightness == end_brightness or duration < 0.001:
            self.set_brightness(end_brightness, monitors)
            return
        brightness_range = end_brightness - start_brightness
        anim_step_duration = duration / abs(brightness_range)
        start_time = time() - anim_step_duration

        while True:
            anim_step_start_time = time()
            if self._all_monitors != sbc.list_monitors():
                return
            progress = (anim_step_start_time - start_time) / duration
            current_brightness = round(start_brightness + progress * brightness_range)
            if progress >= 1.0 or current_brightness == end_brightness:
                self.set_brightness(end_brightness, monitors)
                return
            self.set_brightness(current_brightness, monitors)
            anim_step_end_time = time()
            anim_step_elapsed_time = anim_step_end_time - anim_step_start_time
            await asyncio.sleep(anim_step_duration - anim_step_elapsed_time)

    @staticmethod
    def get_supported_monitors(monitors: list[str] = None) -> list[str]:
        """
        Returns a list of supported monitors from a list of given monitors.
        If monitors is None, the list of all monitors will be used.
        """
        supported_monitors = []
        if monitors is None:
            monitors = sbc.list_monitors()
        for monitor in monitors:
            try:
                sbc.get_brightness(display=monitor)
                supported_monitors.append(monitor)
            except sbc.exceptions.ScreenBrightnessError:
                pass
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
            if not self._supported_monitors:
                windll.user32.MessageBoxW(
                    0,
                    "Error: No supported monitors found",
                    "AutoBrightnessControl",
                    0,
                )
                raise RuntimeError("No supported monitors found")
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

    async def update_monitor_list_task(self):
        """
        Continuously updates the lists of all monitors and supported monitors.
        """
        while True:
            await self.wait_for_task("monitor_list")
            start_time = time()

            self._monitor_list_updated = self.update_monitor_list()

            self.switch_to_next_task()
            end_time = time()
            elapsed_time = end_time - start_time
            self.__sum_elapsed_time += elapsed_time

    async def brightness_control_task(
        self,
        location: LocationInfo,
    ) -> None:
        """
        Continuously controls brightness based on sunrise and sunset.
        """
        time_zone = timezone(location.timezone)
        while True:
            await self.wait_for_task("control")
            start_time = time()

            current_time = datetime.now(time_zone)
            sun_data = sun(location.observer, date=current_time)

            self._base_brightness = self.calculate_base_brightness(
                sun_data["sunrise"],
                sun_data["sunset"],
                current_time,
            )

            self.switch_to_next_task()
            end_time = time()
            elapsed_time = end_time - start_time
            self.__sum_elapsed_time += elapsed_time

    async def brightness_adaptation_task(self) -> None:
        """
        Continuously adapts brightness based on content on the screen.
        """
        import dxcam
        import numpy as np

        # I understand that it's not considered good practice to import modules in a function
        # but in this case it's more efficient because this is an optional task

        pixel_density = 60  # not ppi
        camera = dxcam.create()
        div = round(camera.height / pixel_density)
        brightness_adaptation_range = (self._max - self._min) / 2
        gamma_lut = np.array([(i / 255.0) ** 2.2 for i in range(256)], dtype=np.float32)
        weights = None

        def init_weights(h: int, w: int) -> np.ndarray:
            y, x = np.ogrid[:h, :w]
            center_y, center_x = h // 2, w // 2
            sigma = min(center_x, center_y) / 2
            w_matrix = np.exp(
                -((x - center_x) ** 2 + (y - center_y) ** 2) / (2 * sigma**2),
                dtype=np.float32,
            )
            return w_matrix / w_matrix.sum()

        while True:
            await self.wait_for_task("adaptation")
            start_time = time()

            if self._monitor_list_updated:
                del camera
                camera = dxcam.create()
                div = round(camera.height / pixel_density)
                weights = None
            screenshot = camera.grab()
            if screenshot is not None:
                max_by_subpixels = gamma_lut[
                    np.max(
                        screenshot[::div, ::div],
                        axis=2,
                    )
                ]
                # Get a sub-matrix of pixels with a step of 'div'
                # and then find a subpixel with the highest color value in each pixel

                if weights is None:
                    weights = init_weights(*max_by_subpixels.shape)
                weighted_mean = np.sum(max_by_subpixels * weights)

                brightness_addition = (
                    weighted_mean - 0.5
                ) * brightness_adaptation_range
                # 0 - 255   to   (-1/4 of brightness range) - (1/4 of brightness range)

                self._adapted_brightness = self._base_brightness + brightness_addition
            self.switch_to_next_task()
            end_time = time()
            elapsed_time = end_time - start_time
            self.__sum_elapsed_time += elapsed_time

    async def brightness_update_task(
        self,
    ) -> None:
        """
        Continuously updates the brightness of the display.
        """
        last_brightness = sbc.get_brightness(display=self._supported_monitors[0])[0]
        while True:
            await self.wait_for_task("update")
            start_time = time()

            if self._monitor_list_updated:
                last_brightness = sbc.get_brightness(
                    display=self._supported_monitors[0]
                )[0]
            current_brightness = round(
                self._adapted_brightness if self._is_adaptive else self._base_brightness
            )
            current_brightness = max(
                self._min,
                min(self._max, current_brightness),
            )
            if current_brightness != last_brightness:
                await self.set_brightness_smoothly(
                    last_brightness,
                    current_brightness,
                    min(2.0, self._interval / 2),
                )
                last_brightness = current_brightness
            self.switch_to_next_task()
            end_time = time()
            elapsed_time = end_time - start_time
            self.__sum_elapsed_time += elapsed_time

    async def sleep_task(self) -> None:
        while True:
            await self.wait_for_task("sleep")

            await asyncio.sleep(self._interval - self.__sum_elapsed_time)
            await self.wait_for_unpause()
            self.__sum_elapsed_time = 0.0

            self.switch_to_next_task()

    async def start_main_loop(self, location: LocationInfo) -> None:
        """
        Starts the main loop of the brightness controller.
        """
        async with asyncio.TaskGroup() as tg:
            for task in self._task_queue:
                if task == "monitor_list":
                    tg.create_task(self.update_monitor_list_task())
                elif task == "control":
                    tg.create_task(self.brightness_control_task(location))
                elif task == "adaptation":
                    tg.create_task(self.brightness_adaptation_task())
                elif task == "update":
                    tg.create_task(self.brightness_update_task())
                elif task == "sleep":
                    tg.create_task(self.sleep_task())
