import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nomzy import __version__
from nomzy.main import main, run
from nomzy.macos_overlay import (
    configure_macos_application,
    has_native_macos_windowing,
)
from nomzy.paths import get_assets_dir, get_bundled_config_dir
from nomzy.settings import DEFAULT_SETTINGS, load_settings
from nomzy.speech import DEFAULT_SPEECH, load_speech
from nomzy.storage import read_json_object


class ProjectRuntimeTests(unittest.TestCase):
    def test_release_version(self):
        self.assertEqual(__version__, "0.5.3")

    def test_startup_configures_version_and_defers_overlay_to_show_event(self):
        centered_position = object()

        with (
            patch("nomzy.main.QApplication") as application_class,
            patch("nomzy.main.NomzyDog") as companion_class,
            patch("nomzy.main.configure_macos_application") as configure_macos,
        ):
            application = application_class.return_value
            application.exec.return_value = 0
            companion = companion_class.return_value
            companion.settings = {"macos_hide_dock_icon": True}
            companion.get_saved_position.return_value = None
            companion.get_centered_position.return_value = centered_position

            self.assertEqual(run(["nomzy"]), 0)

        application.setApplicationVersion.assert_called_once_with(__version__)
        configure_macos.assert_called_once_with(hide_dock_icon=True)
        companion.move.assert_called_once_with(centered_position)
        companion.show.assert_called_once_with()
        companion.apply_native_overlay_style.assert_not_called()
        companion.enforce_always_on_top.assert_not_called()

    def test_checkout_resources_are_discoverable(self):
        self.assertTrue((get_assets_dir() / "nomzy_animations.json").is_file())
        self.assertTrue((get_bundled_config_dir() / "speech.json").is_file())

    def test_custom_packaged_resource_root_takes_precedence(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "assets").mkdir()
            (root / "config").mkdir()

            with patch.dict("os.environ", {"NOMZY_RESOURCE_ROOT": str(root)}):
                self.assertEqual(get_assets_dir(), root / "assets")
                self.assertEqual(get_bundled_config_dir(), root / "config")

    def test_invalid_json_is_logged(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "invalid.json"
            path.write_text("not json", encoding="utf-8")

            with self.assertLogs("nomzy.storage", level="WARNING"):
                self.assertIsNone(read_json_object(path))

    def test_invalid_speech_is_logged_and_uses_defaults(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "speech.json"
            path.write_text(json.dumps([]), encoding="utf-8")

            with (
                patch("nomzy.speech.get_speech_path", return_value=path),
                self.assertLogs("nomzy.speech", level="WARNING"),
            ):
                self.assertEqual(load_speech(), DEFAULT_SPEECH)

    def test_invalid_settings_are_logged_and_use_defaults(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            settings_path = root / "user" / "settings.json"
            settings_path.parent.mkdir()
            settings_path.write_text("not json", encoding="utf-8")

            with (
                patch(
                    "nomzy.settings.get_settings_path",
                    return_value=settings_path,
                ),
                patch(
                    "nomzy.settings.get_legacy_settings_path",
                    return_value=root / "bundled" / "settings.json",
                ),
                self.assertLogs("nomzy.storage", level="WARNING"),
            ):
                self.assertEqual(load_settings(), DEFAULT_SETTINGS)

    def test_entry_point_logs_startup_failures(self):
        with (
            patch("nomzy.main.configure_logging"),
            patch("nomzy.main.run", side_effect=RuntimeError("broken")),
            self.assertLogs("nomzy.main", level="ERROR"),
        ):
            self.assertEqual(main(), 1)

    def test_native_macos_integration_requires_the_cocoa_qt_backend(self):
        with (
            patch("nomzy.macos_overlay.is_macos", return_value=True),
            patch(
                "nomzy.macos_overlay.QGuiApplication.platformName",
                return_value="offscreen",
            ),
        ):
            self.assertFalse(has_native_macos_windowing())

    def test_unavailable_macos_integration_is_logged_and_nonfatal(self):
        with (
            patch(
                "nomzy.macos_overlay.has_native_macos_windowing",
                return_value=True,
            ),
            patch.dict(sys.modules, {"AppKit": None}),
            self.assertLogs("nomzy.macos_overlay", level="WARNING"),
        ):
            configure_macos_application()


if __name__ == "__main__":
    unittest.main()
