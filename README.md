Latest version (v1.3.5): https://drive.google.com/file/d/1QnRQdU7UEXbo8nMFklBsfG7q-euMk_ei/view?usp=sharing

The main change in version 1.3.x was adaptive brightness change depending on the content on the screen. I understand that not everyone needs such a function, and in this case I recommend downloading version 1.2.x.

Since the .exe file size in the latest update exceeds the GitHub limit of 100 MB, I uploaded it to Google Drive. The latest update uses an optimized DXcam library for screen capture, which also fixes a bug that disrupts the program when running full-screen applications, including games.

This app is very easy to use, all you have to do is to run brightness_control.exe (unless you want to change something with arguments). You don't need to have python interpreter or any python libraries installed.

You can also create a task in Windows Task Manager to have this app autorun on startup with desired arguments using create_task.bat (run as administrator!!!).

Latitude and longitude are determined by your IP address, not GPS or anything else, so it would be determined incorrectly if you are using a VPN when the app launches.

You can get your coordinates on this website: https://www.latlong.net/

Full list of arguments:

--min - Minimum brightness (default: 20)

--max - Maximum brightness (default: 70)

--speed - Lower values make the transition around sunset and sunrise faster. Recommended value is from 0.5 to 1.0 (default: 1.0)

--lat - Latitude (default: automatic detection)

--lng - Longitude (default: automatic detection)

--log - Enable logging (default: False)

speed = 0.5:
![0 5](https://github.com/user-attachments/assets/d5e40796-5f55-4bdf-9441-119b854e05ff)

speed = 0.75:
![0 75](https://github.com/user-attachments/assets/57bc00d4-cccc-461d-beef-124dccc6212a)

speed = 1.0:
![1 0](https://github.com/user-attachments/assets/41ed7861-4ef0-436b-bdfa-e57a4e782130)

I recommend use it with Auto Dark Mode application, which uses latitude and longitude coordinates too to change Windows theme to dark and light mode automatically. Particularly this application inspired me to create AutoBrightnessControl.

This program has been tested on Windows 10 and 11 only.
