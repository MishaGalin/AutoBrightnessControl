import win32serviceutil
import win32service
import win32event
import subprocess
import os

class BrightnessControlService(win32serviceutil.ServiceFramework):
    _svc_name_ = "BrightnessControlService"
    _svc_display_name_ = "Brightness Control Service"
    _svc_description_ = "Automatically adjusts monitor brightness based on sunrise and sunset."

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        script_path = os.path.abspath("brightness_control.py")
        subprocess.run(["python", script_path])

if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(BrightnessControlService)
