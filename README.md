Usage of this app is super simple, all you have to do is to run the brightness_control.exe file (unless you want to change something via arguments). You don't need to have python interpreter or any python libraries installed.

You can also create a task in Windows Task Manager to have this app autorun on startup with desired arguments using the file create_task.bat (run as administrator!!!).

You can get your coordinates on this website: https://www.latlong.net/

Full list of arguments:

--min - Minimum brightness (default: 20)

--max - Maximum brightness (default: 70)

--speed - Lower values make the transition around sunset and sunrise faster. Recommended value is from 0.5 to 1.0 (default: 1.0)

--lat - Latitude (default: automatic detection)

--lng - Longitude (default: automatic detection)

--log - Enable logging (default: False)

--plot - Enable display of brightness graph (default: False)

speed = 0.5:
![Figure_1](https://github.com/user-attachments/assets/c3da827e-1e55-49d7-bb40-860e07eec6a0)

speed = 0.75:
![Figure_2](https://github.com/user-attachments/assets/302d8ff7-279f-4a75-92ae-141448b50aa6)

speed = 1.0:
![Figure_3png](https://github.com/user-attachments/assets/a74f5940-0927-4287-97be-d011ca277eae)

This program has been tested on Windows 10 and 11 only.
