@echo off
setlocal

:: Определяем путь к текущей папке BAT-файла
set SCRIPT_DIR=%~dp0
set SCRIPT_NAME=script.py
set TASK_NAME=MonitorBrightnessUpdater
set PYTHON_CMD=python

:: Проверяем, существует ли уже задача с указанным именем
schtasks /query /tn %TASK_NAME% >nul 2>&1
if %errorlevel%==0 (
    echo Задача %TASK_NAME% уже существует. Удаляем старую задачу.
    schtasks /delete /tn %TASK_NAME% /f
)

:: Создаем новую задачу
schtasks /create /tn %TASK_NAME% /tr "\"%PYTHON_CMD%\" \"%SCRIPT_DIR%%SCRIPT_NAME%\"" /sc onlogon /rl highest

if %errorlevel%==0 (
    echo Задача %TASK_NAME% успешно создана!
) else (
    echo Ошибка при создании задачи %TASK_NAME%.
)

pause
