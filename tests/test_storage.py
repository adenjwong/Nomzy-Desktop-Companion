import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nomzy.paths import get_user_data_dir
from nomzy.settings import (
    DEFAULT_SETTINGS,
    load_settings,
    normalize_settings,
    save_settings,
)
from nomzy.state import (
    STATE_COORDINATE_LIMIT,
    load_state,
    normalize_state,
    save_state,
)
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
        self.assertEqual(read_json_object(self.user_settings), settings)

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
        self.assertEqual(
            read_json_object(self.user_settings),
            DEFAULT_SETTINGS,
        )

    def test_malformed_settings_are_repaired_individually(self):
        self.write_json(
            self.user_settings,
            {
                "walk_interval_seconds": "invalid",
                "sprite_width": 999,
                "speech_enabled": "false",
                "sleep_chance_percent": -20,
                "speech_bubble_opacity": 200,
                "user_name": "  Aden  ",
                "macos_window_level": ["invalid"],
                "speech_min_ticks": 9000,
                "speech_max_ticks": 1000,
                "unknown_setting": True,
            },
        )

        settings = load_settings()

        self.assertEqual(settings["walk_interval_seconds"], 5)
        self.assertEqual(settings["sprite_width"], 180)
        self.assertTrue(settings["speech_enabled"])
        self.assertEqual(settings["sleep_chance_percent"], 0)
        self.assertEqual(settings["speech_bubble_opacity"], 200)
        self.assertEqual(settings["user_name"], "Aden")
        self.assertEqual(settings["macos_window_level"], "status")
        self.assertEqual(settings["speech_min_ticks"], 1000)
        self.assertEqual(settings["speech_max_ticks"], 9000)
        self.assertNotIn("unknown_setting", settings)
        self.assertEqual(read_json_object(self.user_settings), settings)

    def test_saving_settings_normalizes_values(self):
        save_settings(
            DEFAULT_SETTINGS
            | {
                "sprite_width": 10,
                "always_on_top": False,
                "unknown_setting": True,
            }
        )

        saved_settings = read_json_object(self.user_settings)

        self.assertEqual(saved_settings["sprite_width"], 60)
        self.assertFalse(saved_settings["always_on_top"])
        self.assertNotIn("unknown_setting", saved_settings)

    def test_normalize_settings_uses_defaults_for_non_objects(self):
        self.assertEqual(normalize_settings(None), DEFAULT_SETTINGS)

    def test_state_is_migrated_and_subsequent_saves_use_the_user_path(self):
        legacy_state = {
            "sprite_center_x": 100,
            "sprite_center_y": 200,
            "last_direction": -1,
        }
        self.write_json(self.legacy_state, legacy_state)

        self.assertEqual(load_state(), legacy_state)

        saved_state = {
            "sprite_center_x": 200,
            "sprite_center_y": 300,
            "last_direction": 1,
        }
        save_state(saved_state)

        self.assertEqual(load_state(), saved_state)
        self.assertEqual(
            read_json_object(self.legacy_state),
            legacy_state,
        )

    def test_invalid_position_is_removed_for_safe_fallback(self):
        self.write_json(
            self.user_state,
            {
                "sprite_center_x": "invalid",
                "sprite_center_y": 200,
                "last_direction": -1,
            },
        )

        self.assertEqual(load_state(), {})
        self.assertEqual(read_json_object(self.user_state), {})

    def test_state_coordinates_are_clamped_and_direction_is_repaired(self):
        self.write_json(
            self.user_state,
            {
                "sprite_center_x": STATE_COORDINATE_LIMIT * 2,
                "sprite_center_y": -STATE_COORDINATE_LIMIT * 2,
                "last_direction": 0,
            },
        )

        state = load_state()

        self.assertEqual(state["sprite_center_x"], STATE_COORDINATE_LIMIT)
        self.assertEqual(state["sprite_center_y"], -STATE_COORDINATE_LIMIT)
        self.assertEqual(state["last_direction"], 1)
        self.assertEqual(read_json_object(self.user_state), state)

    def test_normalize_state_rejects_non_integer_coordinates(self):
        self.assertEqual(
            normalize_state(
                {
                    "sprite_center_x": True,
                    "sprite_center_y": 200,
                }
            ),
            {},
        )

    def test_state_preserves_valid_display_relative_position(self):
        state = {
            "sprite_center_x": -800,
            "sprite_center_y": 400,
            "last_direction": -1,
            "screen_id": "serial:ABC123",
            "screen_relative_x": 0.25,
            "screen_relative_y": 0.75,
        }

        self.assertEqual(normalize_state(state), state)

    def test_state_discards_incomplete_display_metadata(self):
        state = {
            "sprite_center_x": 100,
            "sprite_center_y": 200,
            "last_direction": 1,
            "screen_id": "serial:ABC123",
            "screen_relative_x": 2.0,
        }

        self.assertEqual(
            normalize_state(state),
            {
                "sprite_center_x": 100,
                "sprite_center_y": 200,
                "last_direction": 1,
            },
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
