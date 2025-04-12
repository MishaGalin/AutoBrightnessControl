<div align="left">
  <img alt="GitHub License" src="https://img.shields.io/github/license/MishaGalin/AutoBrightnessControl">
  <img alt="GitHub Repo stars" src="https://img.shields.io/github/stars/MishaGalin/AutoBrightnessControl">
</div>

# Environment Setup

- Python 3.11+ required

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

You can also create a task in Windows Task Scheduler to have this app autorun on startup with desired arguments using ```create_task.bat``` (run as administrator) if it is in the same folder as ```AutoBrightnessControl.exe```.

![1](https://github.com/user-attachments/assets/30210b55-9826-4961-930d-660041f9b861)

Latitude, longitude and time zone are determined by your IP address using https://ipinfo.io/json so it would be determined incorrectly if you are using a VPN when the app launches.

To close the application, end the task in Task Manager. 

Launching a new instance of the application will close all existing ones so there will be no brightness control conflicts.

You can get your coordinates on this website: https://www.latlong.net/

Full list of arguments:

```--min``` - Minimum brightness in percent (default: 20)

```--max``` - Maximum brightness in percent (default: 70)

```--speed``` - Lower values make the transition around sunset and sunrise faster. Recommended value is from 0.5 to 1.0 (default: 1.0)

```--lat``` - Latitude (default: automatic detection)

```--lng``` - Longitude (default: automatic detection)

```--adaptive``` - Enable adaptive brightness (default: False)

```--primary-only``` - Brightness changes apply to the primary monitor only (default: False)

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

---

I recommend use it with Auto Dark Mode application, which uses latitude and longitude coordinates too to change Windows theme to dark and light mode automatically. Particularly this application inspired me to create AutoBrightnessControl.

This program has been tested on Windows 10 and 11 only with a single monitor setup. But it should work properly on multi-monitor setups as well.
