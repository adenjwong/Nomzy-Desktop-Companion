import logging
import sys
from ctypes import c_void_p

from PySide6.QtGui import QGuiApplication


LOGGER = logging.getLogger(__name__)


def is_macos() -> bool:
    return sys.platform == "darwin"


def has_native_macos_windowing() -> bool:
    return is_macos() and QGuiApplication.platformName() == "cocoa"


def configure_macos_application(hide_dock_icon: bool = True) -> None:
    if not has_native_macos_windowing():
        return

    try:
        import AppKit

        app = AppKit.NSApplication.sharedApplication()

        if hide_dock_icon:
            app.setActivationPolicy_(
                AppKit.NSApplicationActivationPolicyAccessory
            )

    except Exception as error:
        LOGGER.warning("Could not configure macOS app policy: %s", error)


# QWidget.winId() points to an NSView on macOS, so unwrap its parent NSWindow.
def get_ns_window(qt_widget):
    if not has_native_macos_windowing():
        return None

    try:
        import objc

        native_id = int(qt_widget.winId())
        native_object = objc.objc_object(c_void_p=c_void_p(native_id))

        if hasattr(native_object, "window"):
            ns_window = native_object.window()

            if ns_window is not None:
                return ns_window

        return native_object

    except Exception as error:
        LOGGER.warning("Could not get the macOS NSWindow: %s", error)
        return None


def get_window_level(level_name: str):
    import AppKit

    normalized = str(level_name).strip().lower()

    if normalized == "screen_saver":
        return AppKit.NSScreenSaverWindowLevel

    if normalized == "status":
        return AppKit.NSStatusWindowLevel

    return AppKit.NSFloatingWindowLevel + 1


# Configure the native window because Qt flags do not cover macOS Spaces behavior.
def configure_macos_overlay_window(
    qt_widget,
    window_level: str = "status",
    prevent_activation: bool = True,
) -> None:
    if not has_native_macos_windowing():
        return

    try:
        import AppKit

        ns_window = get_ns_window(qt_widget)

        if ns_window is None:
            LOGGER.warning("No macOS NSWindow was found for the Nomzy overlay")
            return

        if hasattr(ns_window, "setOpaque_"):
            ns_window.setOpaque_(False)

        if hasattr(ns_window, "setBackgroundColor_"):
            ns_window.setBackgroundColor_(AppKit.NSColor.clearColor())

        if hasattr(ns_window, "setLevel_"):
            ns_window.setLevel_(get_window_level(window_level))

        behavior = 0

        behavior |= getattr(
            AppKit,
            "NSWindowCollectionBehaviorCanJoinAllSpaces",
            1 << 0,
        )
        behavior |= getattr(
            AppKit,
            "NSWindowCollectionBehaviorStationary",
            1 << 4,
        )
        behavior |= getattr(
            AppKit,
            "NSWindowCollectionBehaviorFullScreenAuxiliary",
            1 << 8,
        )
        behavior |= getattr(
            AppKit,
            "NSWindowCollectionBehaviorIgnoresCycle",
            1 << 6,
        )

        if hasattr(ns_window, "setCollectionBehavior_"):
            ns_window.setCollectionBehavior_(behavior)

        if prevent_activation and hasattr(ns_window, "styleMask"):
            current_style = ns_window.styleMask()

            nonactivating_panel_mask = getattr(
                AppKit,
                "NSWindowStyleMaskNonactivatingPanel",
                1 << 7,
            )

            ns_window.setStyleMask_(current_style | nonactivating_panel_mask)

        if hasattr(ns_window, "setHidesOnDeactivate_"):
            ns_window.setHidesOnDeactivate_(False)

        if hasattr(ns_window, "setCanHide_"):
            ns_window.setCanHide_(False)

        if hasattr(ns_window, "setReleasedWhenClosed_"):
            ns_window.setReleasedWhenClosed_(False)

        if hasattr(ns_window, "setWorksWhenModal_"):
            ns_window.setWorksWhenModal_(True)

        if hasattr(ns_window, "setBecomesKeyOnlyIfNeeded_"):
            ns_window.setBecomesKeyOnlyIfNeeded_(True)

        if hasattr(ns_window, "setIgnoresMouseEvents_"):
            ns_window.setIgnoresMouseEvents_(False)

        if hasattr(ns_window, "orderFrontRegardless"):
            ns_window.orderFrontRegardless()

    except Exception as error:
        LOGGER.warning("Could not configure the macOS overlay window: %s", error)
