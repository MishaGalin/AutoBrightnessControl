@echo off

:: Task name
set taskOnStartUpName=AutoBrightnessControlTaskOnStartUp
set taskOnWakeUpName=AutoBrightnessControlTaskOnWakeUp

schtasks /delete /tn "%taskOnStartUpName%" /f >nul 2>&1
schtasks /delete /tn "%taskOnWakeUpName%" /f >nul 2>&1

if %errorlevel% equ 0 (
    echo Task "%taskOnStartUpName%" was successfully deleted.
    echo Task "%taskOnWakeUpName%" was successfully deleted.
) else (
    echo Error: Task not found or could not be deleted. Try running with administrator rights.
)

pause