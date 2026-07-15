import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from nomzy.settings import DEFAULT_SETTINGS
from nomzy.settings_window import NomzySettingsWindow


class SettingsWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_walk_interval_loads_from_settings(self):
        settings = DEFAULT_SETTINGS | {"walk_interval_seconds": 45}
        window = NomzySettingsWindow(settings, on_save=None)

        self.assertEqual(window.walk_interval_input.value(), 45)

    def test_walk_interval_is_included_when_settings_are_built(self):
        window = NomzySettingsWindow(DEFAULT_SETTINGS, on_save=None)
        window.walk_interval_input.setValue(90)

        updated_settings = window.build_updated_settings()

        self.assertEqual(updated_settings["walk_interval_seconds"], 90)


if __name__ == "__main__":
    unittest.main()
