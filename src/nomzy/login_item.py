"""The operating system, rather than settings.json, owns login-item state."""
import platform
import logging

LOGGER = logging.getLogger(__name__)
from pathlib import Path

from .macos_overlay import has_native_macos_windowing


class LoginItem:
    def __init__(self):
        self.service = None
        self.unavailable_reason = "Launch at Login requires the Nomzy macOS application bundle on macOS 13 or later."
        if not has_native_macos_windowing():
            return
        try:
            if int(platform.mac_ver()[0].split(".")[0]) < 13:
                return
            from Foundation import NSBundle
            from ServiceManagement import SMAppService

            bundle = NSBundle.mainBundle()
            if (Path(str(bundle.bundlePath())).suffix != ".app"
                    or bundle.bundleIdentifier() != "com.nomzy.desktop-companion"):
                return
            self.service = SMAppService.mainAppService()
        except Exception:
            LOGGER.exception("Could not initialize macOS login service")
            self.unavailable_reason = "Launch at Login is unavailable. Try reopening Nomzy from Applications."

    def status(self):
        if self.service is None:
            return False, self.unavailable_reason
        try:
            status = int(self.service.status())
        except Exception:
            LOGGER.exception("Could not read macOS login-item status")
            return False, "Unable to check Launch at Login. Check System Settings → General → Login Items."
        return status in (1, 2), {
            0: "Nomzy will not launch at login.",
            1: "Nomzy will launch at login.",
            2: "Approval required in System Settings → General → Login Items.",
            3: "macOS could not find this application. Move Nomzy to Applications and try again.",
        }.get(status, "Login-item status is unavailable.")

    def set_enabled(self, enabled):
        if self.service is None:
            raise RuntimeError(self.unavailable_reason)
        try:
            method = self.service.registerAndReturnError_ if enabled else self.service.unregisterAndReturnError_
            success, error = method(None)
            if not success:
                raise RuntimeError(str(error.localizedDescription()) if error else "Service rejected request")
        except Exception:
            LOGGER.exception("Could not update macOS login item (enabled=%s)", enabled)
            raise RuntimeError("Unable to change Launch at Login. Check System Settings → General → Login Items and try again.") from None
        LOGGER.info("Login-item change requested (enabled=%s)", enabled)
