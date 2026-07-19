import json
import os
import tempfile
from pathlib import Path


def read_json_object(path: Path) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as file:
            value = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

    return value if isinstance(value, dict) else None


def write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as file:
            json.dump(value, file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(temporary_path, path)
    except Exception:
        try:
            os.close(file_descriptor)
        except OSError:
            pass
        temporary_path.unlink(missing_ok=True)
        raise


def load_user_json(user_path: Path, legacy_path: Path) -> dict | None:
    if user_path.exists():
        return read_json_object(user_path)

    legacy_value = read_json_object(legacy_path)
    if legacy_value is None:
        return None

    try:
        write_json_atomic(user_path, legacy_value)
    except OSError:
        pass

    return legacy_value
