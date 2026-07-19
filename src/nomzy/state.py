from .paths import get_legacy_state_path, get_state_path
from .storage import load_user_json, write_json_atomic


def load_state() -> dict:
    state = load_user_json(
        get_state_path(),
        get_legacy_state_path(),
    )
    return state or {}


def save_state(state: dict) -> None:
    try:
        write_json_atomic(get_state_path(), state)
    except OSError:
        pass
