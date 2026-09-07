import logging

from .paths import get_legacy_settings_path, get_settings_path
from .storage import load_user_json, write_json_atomic


LOGGER = logging.getLogger(__name__)


DEFAULT_SETTINGS = {
    "window_width": 360,
    "window_height": 190,

    "menu_window_width": 360,
    "menu_window_height": 300,
    "menu_button_radius": 24,
    "menu_arc_radius": 102,

    "sprite_width": 110,
    "sprite_height": 85,

    "user_name": "",

    "always_on_top": True,
    "save_position": True,

    "native_macos_overlay_enabled": True,
    "macos_hide_dock_icon": True,
    "macos_window_level": "status",
    "prevent_focus_steal": True,

    "overlay_mode_enabled": True,
    "overlay_mask_enabled": True,
    "sprite_click_padding": 8,
    "speech_bubble_blocks_input": True,

    "movement_enabled": True,
    "walk_interval_seconds": 5,
    "walk_min_ticks": 10,
    "walk_max_ticks": 35,

    "blink_min_interval_ms": 6000,
    "blink_max_interval_ms": 12000,
    "rest_min_interval_ms": 45000,
    "rest_max_interval_ms": 120000,
    "sleep_chance_percent": 30,

    "speech_enabled": True,
    "speech_min_ticks": 1500,
    "speech_max_ticks": 4500,
    "speech_min_duration_ticks": 75,
    "speech_max_duration_ticks": 125,

    "speech_bubble_opacity": 153,
}

INTEGER_LIMITS = {
    "window_width": (360, 4096),
    "window_height": (190, 2160),
    "menu_window_width": (360, 4096),
    "menu_window_height": (300, 2160),
    "menu_button_radius": (12, 100),
    "menu_arc_radius": (48, 1000),
    "sprite_width": (60, 180),
    "sprite_height": (46, 139),
    "sprite_click_padding": (0, 64),
    "walk_interval_seconds": (5, 300),
    "walk_min_ticks": (1, 250),
    "walk_max_ticks": (1, 250),
    "blink_min_interval_ms": (250, 600000),
    "blink_max_interval_ms": (250, 600000),
    "rest_min_interval_ms": (1000, 3600000),
    "rest_max_interval_ms": (1000, 3600000),
    "sleep_chance_percent": (0, 100),
    "speech_min_ticks": (25, 180000),
    "speech_max_ticks": (25, 180000),
    "speech_min_duration_ticks": (25, 750),
    "speech_max_duration_ticks": (25, 750),
    "speech_bubble_opacity": (26, 255),
}

ORDERED_SETTING_PAIRS = (
    ("walk_min_ticks", "walk_max_ticks"),
    ("blink_min_interval_ms", "blink_max_interval_ms"),
    ("rest_min_interval_ms", "rest_max_interval_ms"),
    ("speech_min_ticks", "speech_max_ticks"),
    ("speech_min_duration_ticks", "speech_max_duration_ticks"),
)


def normalize_settings(settings: dict | None) -> dict:
    raw_settings = settings if isinstance(settings, dict) else {}
    normalized = {}

    for key, default in DEFAULT_SETTINGS.items():
        value = raw_settings.get(key, default)

        if key in INTEGER_LIMITS:
            if type(value) is not int:
                normalized[key] = default
                continue
            minimum, maximum = INTEGER_LIMITS[key]
            normalized[key] = max(minimum, min(value, maximum))
        elif type(default) is bool:
            normalized[key] = value if type(value) is bool else default
        elif key == "user_name":
            normalized[key] = (
                value.strip()[:80]
                if isinstance(value, str)
                else default
            )
        elif key == "macos_window_level":
            allowed_levels = {"floating", "status", "screen_saver"}
            normalized[key] = (
                value
                if isinstance(value, str) and value in allowed_levels
                else default
            )
        else:
            normalized[key] = value if isinstance(value, type(default)) else default

    for minimum_key, maximum_key in ORDERED_SETTING_PAIRS:
        if normalized[minimum_key] > normalized[maximum_key]:
            normalized[minimum_key], normalized[maximum_key] = (
                normalized[maximum_key],
                normalized[minimum_key],
            )

    return normalized


def load_settings() -> dict:
    settings_path = get_settings_path()
    user_settings = load_user_json(
        settings_path,
        get_legacy_settings_path(),
    )
    settings = normalize_settings(user_settings)

    if user_settings != settings:
        try:
            write_json_atomic(settings_path, settings)
        except OSError as error:
            LOGGER.warning("Could not persist repaired settings: %s", error)
    return settings


def save_settings(settings: dict) -> None:
    write_json_atomic(get_settings_path(), normalize_settings(settings))
