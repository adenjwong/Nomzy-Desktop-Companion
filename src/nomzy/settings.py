from .paths import get_legacy_settings_path, get_settings_path
from .storage import load_user_json, write_json_atomic


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

    "speech_bubble_opacity": 145,
}


def load_settings() -> dict:
    settings = DEFAULT_SETTINGS.copy()
    user_settings = load_user_json(
        get_settings_path(),
        get_legacy_settings_path(),
    )
    if user_settings is not None:
        settings.update(user_settings)

    return settings


def save_settings(settings: dict) -> None:
    clean_settings = DEFAULT_SETTINGS.copy()
    clean_settings.update(settings)
    write_json_atomic(get_settings_path(), clean_settings)
