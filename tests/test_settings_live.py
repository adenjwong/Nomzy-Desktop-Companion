import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from nomzy.activity import CompanionEvent, CompanionState
from nomzy.companion import NomzyDog
from nomzy.settings import DEFAULT_SETTINGS


class LiveSettingsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        with patch("nomzy.companion.load_settings", return_value=dict(DEFAULT_SETTINGS)), patch(
            "nomzy.companion.load_speech", return_value={}
        ):
            self.dog = NomzyDog()
        self.addCleanup(self.dog.deleteLater)

    def test_disabling_movement_stops_active_walk_without_resetting_speech(self):
        self.dog.transition_activity(CompanionEvent.START_WALKING)
        self.dog.scheduler.speech_cooldown_ticks = 123
        self.dog.apply_updated_settings(self.dog.settings | {"movement_enabled": False})
        self.assertEqual(self.dog.activity.state, CompanionState.IDLE)
        self.assertEqual(self.dog.walk_step_x, 0)
        self.assertEqual(self.dog.scheduler.speech_cooldown_ticks, 123)

    def test_topmost_flag_and_native_level_follow_setting(self):
        with patch("nomzy.windowing.is_macos", return_value=True), patch(
            "nomzy.windowing.configure_macos_overlay_window"
        ) as native:
            self.dog.apply_updated_settings(self.dog.settings | {"always_on_top": False})
            self.assertFalse(self.dog.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
            self.assertEqual(native.call_args.kwargs["window_level"], "normal")
            self.dog.apply_updated_settings(self.dog.settings | {"always_on_top": True})
            self.assertTrue(self.dog.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
            self.assertEqual(native.call_args.kwargs["window_level"], "status")

    def test_name_change_preserves_walking_countdown_and_timers(self):
        self.dog.scheduler.walk_cooldown_ticks = 7
        timers = [self.dog.timer, self.dog.topmost_timer, self.dog.position_save_timer]
        ids = [timer.timerId() for timer in timers]
        self.dog.apply_updated_settings(self.dog.settings | {"user_name": "Alex"})
        self.assertEqual(self.dog.scheduler.walk_cooldown_ticks, 7)
        self.assertEqual([timer.timerId() for timer in timers], ids)

    def test_reopening_visible_settings_preserves_draft(self):
        self.dog.open_settings_window()
        window = self.dog.settings_window
        self.addCleanup(window.close)
        window.name_input.setText("Alex")
        self.dog.open_settings_window()
        self.assertEqual(window.name_input.text(), "Alex")
        window.cancel()
        self.dog.open_settings_window()
        self.assertEqual(window.name_input.text(), "")
