<div align="left">
  <img alt="GitHub License" src="https://img.shields.io/github/license/MishaGalin/AutoBrightnessControl">
  <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/MishaGalin/AutoBrightnessControl">
</div>

# Environment Setup

```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

# Compile to .exe file

```
pip install pyinstaller
pyinstaller --onefile --noconsole --icon=icon32.ico --name=AutoBrightnessControl brightness_control.py
```

# How to use

All you have to do is to run ```AutoBrightnessControl.exe``` (unless you want to change something with arguments). You don't need to have python interpreter or any python libraries installed. Also, one of the main goals was to keep the application's load on the system almost zero.

You can also create a task in Windows Task Manager to have this app autorun on startup with desired arguments using ```create_task.bat``` (run as administrator) if it is in the same folder as ```AutoBrightnessControl.exe```.

![Screenshot_46](https://github.com/user-attachments/assets/eca81afc-cd2f-45ee-96a2-e526d4d4be4c)

Latitude, longitude and time zone are determined by your IP address using https://ipinfo.io/json so it would be determined incorrectly if you are using a VPN when the app launches.

To close the application, end the task in Task Manager. 

Launching a new instance of the application will close all existing ones so there will be no brightness control conflicts.

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

Periodically capture a screenshot using dxcam and store it in RAM:

```
screenshot = camera.grab()
```

Use a subset of pixels from the screenshot with a step size determined by pixel_density:

```
pixel_density = 60
div = round(camera.height / pixel_density)
pixels = screenshot[::div, ::div]
```

For each pixel, take the maximum value among its subpixels (R, G, B) and apply gamma correction:

```
max_by_subpixels = gamma_lut[np.max(pixels, axis=2)]
```

Use a Gaussian-weighted matrix to prioritize the central area of the screen:

```
weighted_mean = np.sum(max_by_subpixels * weights)
```

Compute the brightness adjustment based on the weighted mean:

```
brightness_addition = (weighted_mean - 0.5) * brightness_adaptation_range
```

Adjust the brightness relative to the base brightness:

```
self.adapted_brightness = self.base_brightness + brightness_addition
```

When setting this brightness to monitors, it will be limited by the minimum and maximum brightness set by the user

```
current_brightness = max(self._min, min(self._max, current_brightness))

await self.set_brightness_smoothly(last_brightness, current_brightness, self.interval / 2)
```

---

I recommend use it with Auto Dark Mode application, which uses latitude and longitude coordinates too to change Windows theme to dark and light mode automatically. Particularly this application inspired me to create AutoBrightnessControl.

This program has been tested on Windows 10 and 11 only with a single monitor setup. But it should work properly on multi-monitor setups as well.
