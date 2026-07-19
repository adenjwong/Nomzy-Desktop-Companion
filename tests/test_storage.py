import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nomzy.paths import get_user_data_dir
from nomzy.settings import DEFAULT_SETTINGS, load_settings, save_settings
from nomzy.state import load_state, save_state
from nomzy.storage import read_json_object, write_json_atomic


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.user_settings = root / "user" / "settings.json"
        self.legacy_settings = root / "legacy" / "settings.json"
        self.user_state = root / "user" / "state.json"
        self.legacy_state = root / "legacy" / "state.json"
        self.patchers = [
            patch("nomzy.settings.get_settings_path", return_value=self.user_settings),
            patch(
                "nomzy.settings.get_legacy_settings_path",
                return_value=self.legacy_settings,
            ),
            patch("nomzy.state.get_state_path", return_value=self.user_state),
            patch(
                "nomzy.state.get_legacy_state_path",
                return_value=self.legacy_state,
            ),
        ]
        for patcher in self.patchers:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patchers):
            patcher.stop()
        self.temporary_directory.cleanup()

    def write_json(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_legacy_settings_are_migrated_once(self):
        self.write_json(self.legacy_settings, {"walk_interval_seconds": 5})

        settings = load_settings()

        self.assertEqual(settings["walk_interval_seconds"], 5)
        self.assertEqual(
            read_json_object(self.user_settings),
            {"walk_interval_seconds": 5},
        )

    def test_existing_user_settings_take_precedence(self):
        self.write_json(self.legacy_settings, {"walk_interval_seconds": 5})
        self.write_json(self.user_settings, {"walk_interval_seconds": 60})

        settings = load_settings()

        self.assertEqual(settings["walk_interval_seconds"], 60)

    def test_saving_settings_does_not_modify_the_legacy_file(self):
        self.write_json(self.legacy_settings, {"walk_interval_seconds": 5})
        settings = DEFAULT_SETTINGS | {"walk_interval_seconds": 90}

        save_settings(settings)

        self.assertEqual(
            read_json_object(self.user_settings)["walk_interval_seconds"],
            90,
        )
        self.assertEqual(
            read_json_object(self.legacy_settings),
            {"walk_interval_seconds": 5},
        )

    def test_invalid_user_settings_fall_back_without_reimporting_legacy_data(self):
        self.write_json(self.legacy_settings, {"walk_interval_seconds": 5})
        self.user_settings.parent.mkdir(parents=True, exist_ok=True)
        self.user_settings.write_text("not json", encoding="utf-8")

        settings = load_settings()

        self.assertEqual(
            settings["walk_interval_seconds"],
            DEFAULT_SETTINGS["walk_interval_seconds"],
        )
        self.assertEqual(self.user_settings.read_text(encoding="utf-8"), "not json")

    def test_state_is_migrated_and_subsequent_saves_use_the_user_path(self):
        self.write_json(self.legacy_state, {"sprite_center_x": 100})

        self.assertEqual(load_state(), {"sprite_center_x": 100})

        save_state({"sprite_center_x": 200})

        self.assertEqual(load_state(), {"sprite_center_x": 200})
        self.assertEqual(
            read_json_object(self.legacy_state),
            {"sprite_center_x": 100},
        )

    def test_atomic_write_leaves_only_the_completed_file(self):
        write_json_atomic(self.user_state, {"last_direction": -1})

        self.assertEqual(
            read_json_object(self.user_state),
            {"last_direction": -1},
        )
        self.assertEqual(list(self.user_state.parent.glob("*.tmp")), [])


class UserDataPathTests(unittest.TestCase):
    def test_user_data_path_uses_qt_app_data_location(self):
        with patch(
            "nomzy.paths.QStandardPaths.writableLocation",
            return_value="/tmp/nomzy-user-data",
        ):
            self.assertEqual(
                get_user_data_dir(),
                Path("/tmp/nomzy-user-data"),
            )


if __name__ == "__main__":
    unittest.main()
