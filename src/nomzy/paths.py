import os
import sys
import sysconfig
from pathlib import Path

from PySide6.QtCore import QStandardPaths


APPLICATION_NAME = "Nomzy Desktop Companion"
ORGANIZATION_NAME = "Nomzy"
RESOURCE_ROOT_ENVIRONMENT_VARIABLE = "NOMZY_RESOURCE_ROOT"


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_resource_roots() -> tuple[Path, ...]:
    roots = []

    configured_root = os.environ.get(RESOURCE_ROOT_ENVIRONMENT_VARIABLE)
    if configured_root:
        roots.append(Path(configured_root).expanduser())

    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        frozen_path = Path(frozen_root)
        roots.extend((frozen_path, frozen_path / "share" / "nomzy"))

    executable_path = Path(sys.executable).resolve()
    roots.append(executable_path.parent.parent / "Resources")
    roots.append(Path(__file__).resolve().parent)
    roots.append(get_repo_root())
    roots.append(Path(sysconfig.get_path("data")) / "share" / "nomzy")

    return tuple(dict.fromkeys(roots))


def get_resource_dir(name: str) -> Path:
    roots = get_resource_roots()
    for root in roots:
        resource_dir = root / name
        if resource_dir.is_dir():
            return resource_dir

    searched = ", ".join(str(root / name) for root in roots)
    raise FileNotFoundError(
        f"Could not find the Nomzy {name} directory; searched: {searched}"
    )


def get_assets_dir() -> Path:
    return get_resource_dir("assets")


def get_bundled_config_dir() -> Path:
    try:
        return get_resource_dir("config")
    except FileNotFoundError:
        # The application has complete built-in defaults. Returning a stable path
        # lets the loaders report missing packaged configuration and recover.
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
