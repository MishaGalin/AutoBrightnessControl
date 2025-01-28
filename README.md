<div align="left">
  <img alt="GitHub License" src="https://img.shields.io/github/license/MishaGalin/AutoBrightnessControl">
  <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/MishaGalin/AutoBrightnessControl">
</div>

# Environment Setup

```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

# How to use

All you have to do is to run ```AutoBrightnessControl.exe``` (unless you want to change something with arguments). You don't need to have python interpreter or any python libraries installed. Also, one of the main goals was to keep the application's load on the system almost zero.

You can also create a task in Windows Task Manager to have this app autorun on startup with desired arguments using ```create_task.bat``` (run as administrator) if it is in the same folder as ```AutoBrightnessControl.exe```.

![Screenshot_46](https://github.com/user-attachments/assets/eca81afc-cd2f-45ee-96a2-e526d4d4be4c)

Latitude, longitude and time zone are determined by your IP address using https://ipinfo.io/json so it would be determined incorrectly if you are using a VPN when the app launches.

To close the application, end the task in Task Manager. Launching a new instance of the application will close all existing ones so that there will be no brightness control conflicts.

You can get your coordinates on this website: https://www.latlong.net/

Full list of arguments:

```--min``` - Minimum brightness (default: 20)

```--max``` - Maximum brightness (default: 70)

```--speed``` - Lower values make the transition around sunset and sunrise faster. Recommended value is from 0.5 to 1.0 (default: 1.0)

```--lat``` - Latitude (default: automatic detection)

```--lng``` - Longitude (default: automatic detection)

```--adapt``` - Enable adaptive brightness (default: False)

```--interval``` - Update interval in seconds (default: 2.0)

---

```
--speed 0.5
```
![0 5](https://github.com/user-attachments/assets/d5e40796-5f55-4bdf-9441-119b854e05ff)

---

```
--speed 0.75
```
![0 75](https://github.com/user-attachments/assets/57bc00d4-cccc-461d-beef-124dccc6212a)

---

```
--speed 1.0
```

![1 0](https://github.com/user-attachments/assets/41ed7861-4ef0-436b-bdfa-e57a4e782130)

# Adaptive brightness: how it works

First, we define a brightness adaptation range equal to half the brightness range set by the user

```
brightness_adaptation_range = (self.max - self.min) / 2
```

Every period of time, the program takes a screenshot of your screen. It is not saved on disk, but only stored in RAM until a new screenshot is taken.

```
screenshot = camera.grab()
```

Next, only a very small part of the pixels is taken from the full screenshot

```
pixel_density = 60
divider = round(screenshot.shape[0] / pixel_density)
pixels = screenshot[divider:-divider:divider, divider:-divider:divider]
```

We take the maximums by subpixels, so that, for example, pixel (0, 0, 255) is equivalent to pixel (255, 255, 255)

```
max_by_subpixels = np.max(pixels, axis=2)
```

Taking the average of these maximums and transforming the ranges, we get how much we want to change the brightness relative to the base brightness (the brightness determined by the time of day)

```
brightness_addition = (
    np.mean(max_by_subpixels) / 255.0 - 0.5
) * brightness_adaptation_range
# 0 - 255   to   (-1/4 of brightness range) - (1/4 of brightness range)

self.adapted_brightness = self.base_brightness + brightness_addition
```

When setting this brightness to monitors, it will be limited by the minimum and maximum brightness set by the user

```
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
```

---

I recommend use it with Auto Dark Mode application, which uses latitude and longitude coordinates too to change Windows theme to dark and light mode automatically. Particularly this application inspired me to create AutoBrightnessControl.

This program has been tested on Windows 10 and 11 only with a single monitor setup. But it should work properly on multi-monitor setups as well.
