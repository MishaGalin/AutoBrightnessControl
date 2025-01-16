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

All you have to do is to run ```brightness_control.exe``` (unless you want to change something with arguments). You don't need to have python interpreter or any python libraries installed. Also, one of the main goals was to keep the application's load on the system almost zero.

You can also create a task in Windows Task Manager to have this app autorun on startup with desired arguments using ```create_task.bat``` (run as administrator) if it is in the same folder as ```brightness_control.exe```.

![Screenshot_30](https://github.com/user-attachments/assets/bb4f7dda-2743-4487-b54d-8563f545abe9)

Latitude and longitude are determined by your IP address using https://ipinfo.io/json so it would be determined incorrectly if you are using a VPN when the app launches.

To close the application, end the task in Task Manager.

You can get your coordinates on this website: https://www.latlong.net/

Full list of arguments:

```--min``` - Minimum brightness (default: 20)

```--max``` - Maximum brightness (default: 70)

```--speed``` - Lower values make the transition around sunset and sunrise faster. Recommended value is from 0.5 to 1.0 (default: 1.0)

```--lat``` - Latitude (default: automatic detection)

```--lng``` - Longitude (default: automatic detection)

```--adj``` - Enable brightness adjustment (default: False)

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

# Brightness adjustment: how it works

First, we define a brightness adjustment range equal to half the brightness range set by the user

```
brightness_addition_range = (self.max - self.min) / 2
```

Every period of time, the program takes a screenshot of your screen

```
screenshot = camera.grab()
```

Next, only a very small part of the pixels is taken from the full screenshot

```
pixel_density = 60
divider = round(screenshot.shape[0] / pixel_density)

# Get a submatrix of pixels with a step of 'divider' excluding the edges
pixels = screenshot[divider::divider, divider::divider]
```

We go through each pixel and take the maximum along its subpixels, so that, for example, pixel (0, 0, 255) is equivalent to pixel (255, 255, 255)

```
max_by_subpixels = np.empty(
    shape=(pixels.shape[0], pixels.shape[1]), dtype=np.uint8
)

for i in range(max_by_subpixels.shape[0]):
    for j in range(max_by_subpixels.shape[1]):
        max_by_subpixels[i][j] = max(pixels[i][j])
```

Taking the average of these maxima and transforming the ranges, we get how much we want to change the brightness relative to the base brightness (the brightness determined by the time of day)

```
brightness_addition = float(
    (np.mean(max_by_subpixels) / 255.0 - 0.5)
    * brightness_addition_range
)
# 0 - 255   to   (-1/4 of brightness range) - (1/4 of brightness range)

self.adjusted_brightness = self.base_brightness + brightness_addition
```

When setting this brightness to monitors, it will be limited by the minimum and maximum brightness set by the user

```
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
```

---

I recommend use it with Auto Dark Mode application, which uses latitude and longitude coordinates too to change Windows theme to dark and light mode automatically. Particularly this application inspired me to create AutoBrightnessControl.

This program has been tested on Windows 10 and 11 only with a single monitor setup. But it should work properly on multi-monitor setups as well.
