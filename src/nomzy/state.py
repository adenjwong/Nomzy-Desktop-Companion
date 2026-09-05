from .paths import get_legacy_state_path, get_state_path
from .storage import load_user_json, write_json_atomic


STATE_COORDINATE_LIMIT = 1000000
STATE_SCREEN_ID_LIMIT = 512


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

    normalized = {
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

    screen_id = state.get("screen_id")
    relative_x = state.get("screen_relative_x")
    relative_y = state.get("screen_relative_y")
    has_valid_screen_position = (
        isinstance(screen_id, str)
        and bool(screen_id.strip())
        and len(screen_id) <= STATE_SCREEN_ID_LIMIT
        and type(relative_x) in {int, float}
        and type(relative_y) in {int, float}
        and 0.0 <= relative_x <= 1.0
        and 0.0 <= relative_y <= 1.0
    )
    if has_valid_screen_position:
        normalized.update(
            {
                "screen_id": screen_id,
                "screen_relative_x": float(relative_x),
                "screen_relative_y": float(relative_y),
            }
        )

    return normalized


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
