"""The operating system, rather than settings.json, owns login-item state."""
import platform
from pathlib import Path

from .macos_overlay import has_native_macos_windowing


class LoginItem:
    def __init__(self):
        self.service = None
        self.unavailable_reason = "Launch at Login requires the Nomzy macOS application bundle on macOS 13 or later."
        if not has_native_macos_windowing():
            return
        if int(platform.mac_ver()[0].split(".")[0]) < 13:
            return
        try:
            from Foundation import NSBundle
            from ServiceManagement import SMAppService

            bundle = NSBundle.mainBundle()
            if (Path(str(bundle.bundlePath())).suffix != ".app"
                    or bundle.bundleIdentifier() != "com.nomzy.desktop-companion"):
                return
            self.service = SMAppService.mainAppService()
        except ImportError:
            self.unavailable_reason = "The ServiceManagement dependency is missing. Reinstall Nomzy."

    def status(self):
        if self.service is None:
            return False, self.unavailable_reason
        status = int(self.service.status())
        return status in (1, 2), {
            0: "Nomzy will not launch at login.",
            1: "Nomzy will launch at login.",
            2: "Approval required in System Settings → General → Login Items.",
            3: "macOS could not find this application. Move Nomzy to Applications and try again.",
        }.get(status, "Login-item status is unavailable.")

    def set_enabled(self, enabled):
        if self.service is None:
            raise RuntimeError(self.unavailable_reason)
        method = self.service.registerAndReturnError_ if enabled else self.service.unregisterAndReturnError_
        success, error = method(None)
        if not success:
            raise RuntimeError(str(error.localizedDescription()) if error else "macOS could not update the login item.")
