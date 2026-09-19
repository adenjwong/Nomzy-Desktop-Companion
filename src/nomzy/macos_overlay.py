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

    if normalized == "normal":
        return AppKit.NSNormalWindowLevel

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
    force: bool = False,
) -> None:
    if not has_native_macos_windowing():
        return

    try:
        import AppKit

        ns_window = get_ns_window(qt_widget)

        if ns_window is None:
            LOGGER.warning("No macOS NSWindow was found for the Nomzy overlay")
            return

        signature = (int(ns_window.windowNumber()), window_level, prevent_activation)
        if not force and getattr(qt_widget, "_native_overlay_signature", None) == signature:
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

        if hasattr(ns_window, "styleMask"):
            current_style = ns_window.styleMask()

            nonactivating_panel_mask = getattr(
                AppKit,
                "NSWindowStyleMaskNonactivatingPanel",
                1 << 7,
            )

            desired_style = (current_style | nonactivating_panel_mask) if prevent_activation else (current_style & ~nonactivating_panel_mask)
            if desired_style != current_style:
                ns_window.setStyleMask_(desired_style)

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

        qt_widget._native_overlay_signature = signature

    except Exception as error:
        LOGGER.warning("Could not configure the macOS overlay window: %s", error)


def raise_macos_overlay(widget):
    """An explicit Locate action may order the overlay without activating its app."""
    if not has_native_macos_windowing():
        return False
    try:
        window = get_ns_window(widget)
        if window is not None:
            window.orderFrontRegardless()
            return True
    except Exception as error:
        LOGGER.warning("Could not order the macOS overlay: %s", error)
    return False


def prepare_settings_window(widget):
    """Bring an explicitly requested utility window to the current Space."""
    if not has_native_macos_windowing():
        return
    try:
        import AppKit

        window = get_ns_window(widget)
        if window is not None:
            window.setCollectionBehavior_(
                AppKit.NSWindowCollectionBehaviorMoveToActiveSpace
                | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
            )
    except Exception as error:
        LOGGER.warning("Could not configure utility window Spaces behavior: %s", error)


def activate_settings_window(widget):
    """Explicit user action may activate the accessory app for keyboard input."""
    if not has_native_macos_windowing():
        return
    try:
        import AppKit

        AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        window = get_ns_window(widget)
        if window is not None:
            window.makeKeyAndOrderFront_(None)
    except Exception as error:
        LOGGER.warning("Could not activate settings window: %s", error)
