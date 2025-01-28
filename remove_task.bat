@echo off

set taskName=BrightnessControlTask

schtasks /delete /tn "%taskName%" /f >nul 2>&1

if %errorlevel% equ 0 (
    echo Task "%taskName%" was successfully deleted.
) else (
    echo Error: Task "%taskName%" not found or could not be deleted. Try running with administrator rights.
)

pause