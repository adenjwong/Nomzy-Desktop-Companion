import sys
from ctypes import c_void_p


def is_macos() -> bool:
    return sys.platform == "darwin"


def configure_macos_application(hide_dock_icon: bool = True) -> None:
    """
    Makes the running Python/Qt app behave more like a background accessory app
    on macOS instead of a normal foreground application.
    """
    if not is_macos():
        return

    try:
        import AppKit

        app = AppKit.NSApplication.sharedApplication()

        if hide_dock_icon:
            app.setActivationPolicy_(
                AppKit.NSApplicationActivationPolicyAccessory
            )

    except Exception as error:
        print(f"[Nomzy macOS] Could not configure app policy: {error}")


def get_ns_window(qt_widget):
    """
    Gets the native macOS NSWindow behind a PySide6 QWidget.

    On macOS, QWidget.winId() usually returns a pointer to an NSView.
    That NSView has a .window() method that gives us the NSWindow.
    """
    if not is_macos():
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
        print(f"[Nomzy macOS] Could not get NSWindow: {error}")
        return None


def get_window_level(level_name: str):
    """
    Converts a friendly setting name into a macOS window level.

    floating:
        Above normal app windows.

    status:
        Stronger overlay level. Usually better for desktop companions.

    screen_saver:
        Very aggressive. Use only if Nomzy still falls behind things.
    """
    import AppKit

    normalized = str(level_name).strip().lower()

    if normalized == "screen_saver":
        return AppKit.NSScreenSaverWindowLevel

    if normalized == "status":
        return AppKit.NSStatusWindowLevel

    return AppKit.NSFloatingWindowLevel + 1


def configure_macos_overlay_window(
    qt_widget,
    window_level: str = "status",
    prevent_activation: bool = True,
) -> None:
    """
    Applies macOS-native overlay behavior to the Qt window.

    Goal:
    - stay above normal windows
    - join all spaces/desktops
    - avoid becoming the active application
    - remain visible when other apps are active
    """
    if not is_macos():
        return

    try:
        import AppKit

        ns_window = get_ns_window(qt_widget)

        if ns_window is None:
            print("[Nomzy macOS] No NSWindow found.")
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
        print(f"[Nomzy macOS] Could not configure overlay window: {error}")