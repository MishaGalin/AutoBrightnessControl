@echo off

:: Get arguments from the user
set /p args=Enter arguments for AutoBrightnessControl.exe (skip to use default values):

:: Get the current folder path
set currentPath=%~dp0
set exePath=%currentPath%AutoBrightnessControl.exe

:: Check if AutoBrightnessControl.exe exists
if not exist "%exePath%" (
    echo Error: File AutoBrightnessControl.exe not found in folder %currentPath%.
    pause
    exit /b
)

:: Task names
set taskOnStartUpName=AutoBrightnessControlTaskOnStartUp
set taskOnWakeUpName=AutoBrightnessControlTaskOnWakeUp

:: Delete existing tasks with the same name (if any)
schtasks /delete /tn "%taskOnStartUpName%" /f >nul 2>&1
schtasks /delete /tn "%taskOnWakeUpName%" /f >nul 2>&1

:: Create new tasks
schtasks /create /tn "%taskOnStartUpName%" /tr "\"%exePath%\" %args%" /sc onlogon /rl highest >nul 2>&1
schtasks /create /sc onevent /rl highest >nul 2>&1 /mo "*[System[Provider[@Name='Microsoft-Windows-Kernel-Power'] and EventID=107]]" /ec System /tn "%taskOnWakeUpName%" /tr "\"%exePath%\" %args%" /delay 0000:01

:: Check if the tasks was created successfully
if %errorlevel% equ 0 (
    echo Task successfully created and will run AutoBrightnessControl.exe at system logon.
    echo Running the created task now...
    schtasks /run /tn "%taskOnStartUpName%"
) else (
    echo Error while creating the task. Try running with administrator rights.
)

pause