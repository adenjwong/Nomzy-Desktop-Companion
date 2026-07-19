from pathlib import Path

from PySide6.QtCore import QStandardPaths


APPLICATION_NAME = "Nomzy Desktop Companion"
ORGANIZATION_NAME = "Nomzy"


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_assets_dir() -> Path:
    return get_repo_root() / "assets"


def get_bundled_config_dir() -> Path:
    return get_repo_root() / "config"


def get_user_data_dir() -> Path:
    location = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    if location:
        return Path(location)

    return Path.home() / ".nomzy"


def get_settings_path() -> Path:
    return get_user_data_dir() / "settings.json"


def get_legacy_settings_path() -> Path:
    return get_bundled_config_dir() / "settings.json"


def get_speech_path() -> Path:
    return get_bundled_config_dir() / "speech.json"


def get_state_path() -> Path:
    return get_user_data_dir() / "state.json"


def get_legacy_state_path() -> Path:
    return get_bundled_config_dir() / "state.json"


def get_animation_manifest_path() -> Path:
    return get_assets_dir() / "nomzy_animations.json"
