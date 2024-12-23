@echo off

:: Get arguments from the user
set /p args=Enter arguments for brightness_control.exe (skip to use default values):

:: Get the current folder path
set currentPath=%~dp0
set exePath=%currentPath%brightness_control.exe

:: Check if brightness_control.exe exists
if not exist "%exePath%" (
    echo Error: File brightness_control.exe not found in folder %currentPath%.
    pause
    exit /b
)

:: Task name
set taskName=BrightnessControlTask

:: Delete existing task with the same name (if any)
schtasks /delete /tn "%taskName%" /f >nul 2>&1

:: Create a new task
schtasks /create /tn "%taskName%" /tr "\"%exePath%\" %args%" /sc onlogon /rl highest >nul 2>&1

:: Check if the task was created successfully
if %errorlevel% equ 0 (
    echo Task successfully created and will run brightness_control.exe at system logon.
    echo Running the created task now...
    schtasks /run /tn "%taskName%"
) else (
    echo Error while creating the task.
)

pause