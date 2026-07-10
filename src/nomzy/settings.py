import json

from .paths import get_settings_path


DEFAULT_SETTINGS = {
    "window_width": 360,
    "window_height": 190,

    "menu_window_width": 360,
    "menu_window_height": 300,
    "menu_button_radius": 24,
    "menu_arc_radius": 102,

    "sprite_width": 110,
    "sprite_height": 85,

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
    "idle_min_ticks": 120,
    "idle_max_ticks": 400,
    "walk_min_ticks": 10,
    "walk_max_ticks": 35,

    "speech_enabled": True,
    "speech_min_ticks": 1500,
    "speech_max_ticks": 4500,
    "speech_min_duration_ticks": 75,
    "speech_max_duration_ticks": 125,

    "speech_bubble_opacity": 145,
}


def load_settings() -> dict:
    settings_path = get_settings_path()
    settings = DEFAULT_SETTINGS.copy()

    if not settings_path.exists():
        return settings

    try:
        with open(settings_path, "r", encoding="utf-8") as file:
            user_settings = json.load(file)

        if isinstance(user_settings, dict):
            settings.update(user_settings)

    except Exception:
        pass

    return settings