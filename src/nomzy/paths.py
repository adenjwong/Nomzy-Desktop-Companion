from pathlib import Path


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_assets_dir() -> Path:
    return get_repo_root() / "assets"


def get_config_dir() -> Path:
    return get_repo_root() / "config"


def get_settings_path() -> Path:
    return get_config_dir() / "settings.json"


def get_speech_path() -> Path:
    return get_config_dir() / "speech.json"


def get_state_path() -> Path:
    return get_config_dir() / "state.json"


def get_sprite_sheet_path() -> Path:
    return get_assets_dir() / "nomzy_sprite_sheet.png"


def get_animation_manifest_path() -> Path:
    return get_assets_dir() / "nomzy_animations.json"
