import json

from .paths import get_state_path


def load_state() -> dict:
    state_path = get_state_path()

    if not state_path.exists():
        return {}

    try:
        with open(state_path, "r", encoding="utf-8") as file:
            state = json.load(file)

        if isinstance(state, dict):
            return state

    except Exception:
        pass

    return {}


def save_state(state: dict) -> None:
    state_path = get_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(state_path, "w", encoding="utf-8") as file:
            json.dump(state, file, indent=2)

    except Exception:
        pass