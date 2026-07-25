from .paths import get_legacy_state_path, get_state_path
from .storage import load_user_json, write_json_atomic


STATE_COORDINATE_LIMIT = 1000000


def normalize_state(state: dict | None) -> dict:
    if not isinstance(state, dict):
        return {}

    center_x = state.get("sprite_center_x")
    center_y = state.get("sprite_center_y")
    if type(center_x) is not int or type(center_y) is not int:
        return {}

    direction = state.get("last_direction", 1)
    if type(direction) is not int or direction not in {-1, 1}:
        direction = 1

    return {
        "sprite_center_x": max(
            -STATE_COORDINATE_LIMIT,
            min(center_x, STATE_COORDINATE_LIMIT),
        ),
        "sprite_center_y": max(
            -STATE_COORDINATE_LIMIT,
            min(center_y, STATE_COORDINATE_LIMIT),
        ),
        "last_direction": direction,
    }


def load_state() -> dict:
    state_path = get_state_path()
    state = load_user_json(
        state_path,
        get_legacy_state_path(),
    )
    normalized = normalize_state(state)

    if state != normalized:
        try:
            write_json_atomic(state_path, normalized)
        except OSError:
            pass
    return normalized


def save_state(state: dict) -> None:
    try:
        write_json_atomic(get_state_path(), normalize_state(state))
    except OSError:
        pass
