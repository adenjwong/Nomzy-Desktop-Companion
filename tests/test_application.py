import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QLockFile, QPoint, QTimer
from PySide6.QtWidgets import QApplication

from nomzy.activity import CompanionEvent
from nomzy.application import ApplicationController
from nomzy.companion import NomzyDog
from nomzy.settings import DEFAULT_SETTINGS
from nomzy.login_item import LoginItem


class ApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def controller(self):
        controller = ApplicationController(self.app)
        self.addCleanup(controller.shutdown)
        self.addCleanup(controller.deleteLater)
        return controller

    def test_lock_prevents_duplicate_and_releases_for_relaunch(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch("nomzy.application.get_user_data_dir", return_value=Path(directory)), \
                patch("nomzy.application.NomzyDog") as dog, \
                patch.object(ApplicationController, "create_menu_bar"), \
                patch("nomzy.application.configure_macos_application"):
            dog.return_value.settings = DEFAULT_SETTINGS
            dog.return_value.get_saved_position.return_value = QPoint(10, 20)
            dog.return_value.findChildren.return_value = []
            first = self.controller()
            second = self.controller()
            self.assertTrue(first.start())
            self.assertFalse(second.start())
            self.assertEqual(dog.call_count, 1)
            first.shutdown()
            third = self.controller()
            self.assertTrue(third.start())
            third.shutdown()

    def test_menu_routes_and_refreshes_external_pause_changes(self):
        controller = self.controller()
        controller.nomzy = Mock()
        controller.nomzy.findChildren.return_value = []
        controller.create_menu_bar()
        actions = {a.text(): a for a in controller.menu.actions()}
        actions["Pause Nomzy"].trigger()
        controller.nomzy.toggle_pause.assert_called_once()
        actions["Settings…"].trigger()
        controller.nomzy.open_settings_window.assert_called_once()
        controller.nomzy.activity.paused = True
        controller.refresh_menu()
        self.assertEqual(controller.pause_action.text(), "Resume Nomzy")
        actions["Show / Locate Nomzy"].trigger()
        controller.nomzy.show.assert_called_once()
        controller.nomzy.activateWindow.assert_not_called()

    def test_shutdown_saves_once_even_if_save_fails_and_stops_timers(self):
        controller = self.controller()
        controller.nomzy = Mock()
        timer = Mock()
        controller.nomzy.findChildren.return_value = [timer]
        controller.nomzy.save_state.side_effect = OSError("disk full")
        controller.lock = Mock()
        with self.assertLogs("nomzy.application", level="ERROR"):
            controller.shutdown()
        controller.shutdown()
        controller.nomzy.save_state.assert_called_once()
        timer.stop.assert_called_once()
        controller.lock.unlock.assert_called_once()

    def test_real_companion_shutdown_and_settings_close(self):
        with patch("nomzy.companion.load_settings", return_value=dict(DEFAULT_SETTINGS)), \
                patch("nomzy.windowing.write_state") as save:
            controller = self.controller()
            controller.nomzy = NomzyDog()
            self.addCleanup(controller.nomzy.deleteLater)
            controller.nomzy.show()
            controller.nomzy.open_settings_window()
            controller.nomzy.settings_window.close()
            self.assertTrue(controller.nomzy.isVisible())
            self.assertFalse(controller.stopped)
            controller.nomzy.toggle_pause()
            controller.shutdown()
            save.assert_called_once()
            self.assertTrue(all(not timer.isActive() for timer in controller.nomzy.findChildren(QTimer)))

    def test_about_reuses_one_window_and_closes_with_ok(self):
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QDialogButtonBox
        controller = self.controller()
        controller.nomzy = Mock()
        controller.nomzy.findChildren.return_value = []
        controller.nomzy.get_scaled_sprite.return_value = QPixmap(110, 85)
        controller.show_about()
        window = controller.about_window
        self.addCleanup(window.deleteLater)
        controller.show_about()
        self.assertIs(controller.about_window, window)
        self.assertTrue(window.isVisible())
        window.buttons.button(QDialogButtonBox.StandardButton.Ok).click()
        self.assertFalse(window.isVisible())
        self.assertFalse(controller.stopped)
        controller.show_about()
        self.assertTrue(window.isVisible())

    def test_save_and_relaunch_from_every_activity(self):
        events = [None, CompanionEvent.START_WALKING, CompanionEvent.START_BLINKING,
                  CompanionEvent.START_SITTING, CompanionEvent.START_SLEEPING,
                  CompanionEvent.START_TALKING, CompanionEvent.START_REACTION,
                  CompanionEvent.START_DRAGGING, CompanionEvent.PAUSE,
                  CompanionEvent.OPEN_MENU]
        for event in events:
            with self.subTest(event=event), tempfile.TemporaryDirectory() as directory, \
                    patch("nomzy.application.get_user_data_dir", return_value=Path(directory)), \
                    patch("nomzy.state.get_state_path", return_value=Path(directory) / "state.json"), \
                    patch("nomzy.companion.load_settings", return_value=dict(DEFAULT_SETTINGS)), \
                    patch.object(ApplicationController, "create_menu_bar"), \
                    patch("nomzy.application.configure_macos_application"):
                first = self.controller()
                self.assertTrue(first.start())
                self.addCleanup(first.nomzy.deleteLater)
                if event is not None:
                    first.nomzy.transition_activity(event)
                first.nomzy.move(100, 100)
                center = first.nomzy.get_sprite_global_center()
                first.shutdown()
                second = self.controller()
                self.assertTrue(second.start())
                self.addCleanup(second.nomzy.deleteLater)
                self.assertLessEqual((second.nomzy.get_sprite_global_center() - center).manhattanLength(), 2)
                second.shutdown()


class LoginItemTests(unittest.TestCase):
    def service(self):
        with patch("nomzy.login_item.has_native_macos_windowing", return_value=False):
            item = LoginItem()
        item.service = Mock()
        return item

    def test_status_includes_system_approval(self):
        item = self.service()
        for status, enabled in [(0, False), (1, True), (2, True), (3, False)]:
            item.service.status.return_value = status
            self.assertEqual(item.status()[0], enabled)
        item.service.status.return_value = 2
        self.assertIn("Approval required", item.status()[1])

    def test_register_unregister_and_failure(self):
        item = self.service()
        item.service.registerAndReturnError_.return_value = (True, None)
        item.service.unregisterAndReturnError_.return_value = (True, None)
        item.set_enabled(True)
        item.set_enabled(False)
        item.service.registerAndReturnError_.assert_called_once_with(None)
        item.service.unregisterAndReturnError_.assert_called_once_with(None)
        error = Mock()
        error.localizedDescription.return_value = "Permission denied"
        item.service.registerAndReturnError_.return_value = (False, error)
        with self.assertRaisesRegex(RuntimeError, "Permission denied"):
            item.set_enabled(True)
