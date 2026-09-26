"""Release lifecycle regressions, isolated from real user preferences."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QStandardPaths
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from nomzy import __version__
from nomzy.about_window import AboutWindow
from nomzy.paths import APPLICATION_NAME, ORGANIZATION_NAME, get_user_data_dir
from nomzy.settings import load_settings, save_settings
from nomzy.state import load_state
from nomzy.storage import write_json_atomic


class InstallationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setApplicationName(APPLICATION_NAME)
        cls.app.setOrganizationName(ORGANIZATION_NAME)

    def test_about_shows_running_version(self):
        window = AboutWindow(QPixmap(1, 1))
        self.assertEqual(window.version_label.text(), f"Version {__version__}")
        window.close()

    def test_source_and_frozen_use_same_data_location(self):
        source = get_user_data_dir()
        with patch("sys.frozen", True, create=True), patch("sys.executable", "/Applications/Nomzy.app/Contents/MacOS/Nomzy"):
            self.assertEqual(source, get_user_data_dir())
        self.assertEqual(source, Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)))

    def test_repository_migration_then_app_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo/config"
            bundle = root / "Nomzy.app/Contents/Resources/config"
            user = root / "user"
            write_json_atomic(repo / "settings.json", {"user_name": "Migration test", "speech_enabled": False})
            write_json_atomic(repo / "state.json", {"sprite_center_x": 123, "sprite_center_y": 456, "last_direction": -1})
            originals = {p.name: p.read_bytes() for p in repo.iterdir()}
            with patch("nomzy.paths.get_user_data_dir", return_value=user):
                with patch("nomzy.paths.get_bundled_config_dir", return_value=repo):
                    migrated = load_settings()
                    state = load_state()
                self.assertEqual(migrated["user_name"], "Migration test")
                self.assertFalse(migrated["speech_enabled"])
                self.assertEqual(state["sprite_center_x"], 123)
                save_settings(migrated | {"user_name": "Updated preference"})
                saved = {p.name: p.read_bytes() for p in user.iterdir()}
                write_json_atomic(bundle / "settings.json", {"user_name": "New defaults"})
                with patch("sys.frozen", True, create=True), patch("nomzy.paths.get_bundled_config_dir", return_value=bundle):
                    self.assertEqual(load_settings()["user_name"], "Updated preference")
                    self.assertEqual(load_state(), state)
                self.assertEqual(saved, {p.name: p.read_bytes() for p in user.iterdir()})
                self.assertEqual(originals, {p.name: p.read_bytes() for p in repo.iterdir()})

    def test_failed_atomic_replacement_keeps_previous_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            write_json_atomic(path, {"user_name": "Original"})
            original = path.read_bytes()
            with patch("nomzy.storage.os.replace", side_effect=OSError("disk unavailable")):
                with self.assertRaises(OSError):
                    write_json_atomic(path, {"user_name": "New"})
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.iterdir()), [path])
