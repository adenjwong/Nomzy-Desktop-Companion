import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from nomzy.settings import DEFAULT_SETTINGS
from nomzy.settings_window import NomzySettingsWindow


class SettingsWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_small_display_keeps_actions_visible_and_pages_scrollable(self):
        window = NomzySettingsWindow(DEFAULT_SETTINGS, None)
        self.addCleanup(window.close)
        screen = Mock()
        screen.availableGeometry.return_value = QRect(0, 0, 640, 360)
        window.present(screen)
        self.app.processEvents()
        self.assertTrue(screen.availableGeometry().contains(window.frameGeometry()))
        for index in range(window.tabs.count()):
            window.tabs.setCurrentIndex(index)
            self.app.processEvents()
            scroll = window.tabs.currentWidget()
            self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
            self.assertTrue(window.rect().contains(window.apply_button.geometry()))
        self.assertGreater(window.tabs.currentWidget().verticalScrollBar().maximum(), 0)

    def test_present_restores_minimized_draft_and_focus(self):
        window = NomzySettingsWindow(DEFAULT_SETTINGS, None)
        self.addCleanup(window.close)
        window.present()
        window.name_input.setText("Alex")
        window.size_slider.setFocus()
        window.showMinimized()
        window.present()
        self.app.processEvents()
        self.assertFalse(window.isMinimized())
        self.assertEqual(window.name_input.text(), "Alex")
        self.assertEqual(window.focusWidget(), window.size_slider)

    def test_tab_navigation_and_pending_numeric_text_apply(self):
        window = NomzySettingsWindow(DEFAULT_SETTINGS, None)
        self.addCleanup(window.close)
        window.present()
        window.name_input.setFocus()
        QTest.keyClick(window.name_input, Qt.Key.Key_Tab)
        self.assertEqual(window.focusWidget(), window.size_slider)
        window.tabs.setCurrentIndex(1)
        window.walk_interval_input.lineEdit().setText("90 seconds")
        with patch("nomzy.settings_window.save_settings") as save:
            window.apply_draft()
        self.assertEqual(save.call_args.args[0]["walk_interval_seconds"], 90)
        self.assertEqual(window.walk_interval_input.decimals(), 0)

    def test_walk_interval_loads_from_settings(self):
        settings = DEFAULT_SETTINGS | {"walk_interval_seconds": 45}
        window = NomzySettingsWindow(settings, on_save=None)

        self.assertEqual(window.walk_interval_input.value(), 45)

    def test_walk_interval_is_included_when_settings_are_built(self):
        window = NomzySettingsWindow(DEFAULT_SETTINGS, on_save=None)
        window.walk_interval_input.setValue(90)

        updated_settings = window.build_updated_settings()

        self.assertEqual(updated_settings["walk_interval_seconds"], 90)

    def test_loading_and_no_op_apply_preserve_precise_values(self):
        settings = DEFAULT_SETTINGS | {
            "speech_min_ticks": 1501, "rest_min_interval_ms": 45001,
            "walk_min_ticks": 12, "speech_bubble_opacity": 147,
        }
        window = NomzySettingsWindow(settings, None)
        self.assertEqual(window.build_updated_settings(), settings)
        self.assertEqual(window.speech_min_input.value(), 60.04)
        self.assertEqual(window.tabs.count(), 4)

    def test_apply_saves_normalized_values_and_keeps_window_open(self):
        callback = Mock()
        window = NomzySettingsWindow(DEFAULT_SETTINGS, callback)
        window.show()
        window.name_input.setText("  Alex  ")
        window.controls["movement_enabled"].setChecked(False)
        with patch("nomzy.settings_window.save_settings") as save:
            window.apply_button.click()
        self.assertEqual(save.call_args.args[0]["user_name"], "Alex")
        self.assertFalse(save.call_args.args[0]["movement_enabled"])
        callback.assert_called_once_with(save.call_args.args[0])
        self.assertTrue(window.isVisible())
        self.assertEqual(window.status_label.text(), "Settings applied.")
        window.close()

    def test_cancel_and_close_discard_without_writing(self):
        for action in ("cancel", "close"):
            with self.subTest(action=action):
                callback = Mock()
                window = NomzySettingsWindow(DEFAULT_SETTINGS, callback)
                window.show()
                window.name_input.setText("Discard me")
                with patch("nomzy.settings_window.save_settings") as save:
                    getattr(window, action)()
                save.assert_not_called()
                callback.assert_not_called()
                self.assertEqual(window.build_updated_settings(), DEFAULT_SETTINGS)

    def test_defaults_are_a_cancellable_draft_and_keep_internal_settings(self):
        settings = DEFAULT_SETTINGS | {"user_name": "Alex", "macos_window_level": "floating"}
        window = NomzySettingsWindow(settings, None)
        with patch("nomzy.settings_window.save_settings") as save:
            window.reset_defaults()
            save.assert_not_called()
            self.assertEqual(window.build_updated_settings()["user_name"], "")
            self.assertEqual(window.build_updated_settings()["macos_window_level"], "floating")
            window.cancel()
            self.assertEqual(window.build_updated_settings(), settings)
            window.reset_defaults()
            window.apply_draft()
            self.assertEqual(window.settings["user_name"], "")

    def test_cancel_returns_to_last_applied_snapshot(self):
        window = NomzySettingsWindow(DEFAULT_SETTINGS, None)
        window.name_input.setText("Alex")
        with patch("nomzy.settings_window.save_settings"):
            window.apply_draft()
        window.name_input.setText("Other")
        window.cancel()
        self.assertEqual(window.name_input.text(), "Alex")

    def test_range_controls_prevent_contradictions_in_both_directions(self):
        window = NomzySettingsWindow(DEFAULT_SETTINGS, None)
        for low_key, high_key in (
            ("speech_min_ticks", "speech_max_ticks"),
            ("speech_min_duration_ticks", "speech_max_duration_ticks"),
            ("rest_min_interval_ms", "rest_max_interval_ms"),
            ("blink_min_interval_ms", "blink_max_interval_ms"),
        ):
            low, high = window.controls[low_key], window.controls[high_key]
            low.setValue(high.value() + 1)
            self.assertEqual(low.value(), high.value())
            high.setValue(low.value() - 1)
            self.assertEqual(low.value(), high.value())

    def test_opacity_uses_whole_percentages_with_visible_bounds(self):
        window = NomzySettingsWindow(DEFAULT_SETTINGS, None)
        opacity = window.controls["speech_bubble_opacity"]
        self.assertEqual(opacity.value(), 60)
        self.assertEqual(opacity.decimals(), 0)
        opacity.setValue(0)
        self.assertEqual(opacity.value(), 10)
        self.assertEqual(window.build_updated_settings()["speech_bubble_opacity"], 26)
        opacity.setValue(101)
        self.assertEqual(opacity.value(), 100)
        self.assertEqual(window.build_updated_settings()["speech_bubble_opacity"], 255)
        window.reset_defaults()
        self.assertEqual(opacity.value(), 60)

    def test_save_failure_keeps_edits_without_applying(self):
        callback = Mock()
        window = NomzySettingsWindow(DEFAULT_SETTINGS, callback)
        window.name_input.setText("Alex")
        with patch("nomzy.settings_window.save_settings", side_effect=OSError):
            window.apply_draft()
        callback.assert_not_called()
        self.assertEqual(window.settings, DEFAULT_SETTINGS)
        self.assertEqual(window.name_input.text(), "Alex")
        self.assertIn("Could not save", window.status_label.text())


if __name__ == "__main__":
    unittest.main()
