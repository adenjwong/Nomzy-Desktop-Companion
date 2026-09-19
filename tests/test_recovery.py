import logging
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication

from nomzy.application import ApplicationController
from nomzy.animation import AnimationPlayer
from nomzy.activity import CompanionStateMachine
from nomzy.diagnostics import configure_logging, log_unhandled_exception
from nomzy.login_item import LoginItem
from nomzy.sprites import load_sprite_assets
from nomzy.storage import read_json_object


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_unreadable_manifest_and_source_recover_without_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "nomzy_animations.json"
            for contents in (None, b"\xff", b"{}", b"[]", b"invalid"):
                if contents is not None:
                    manifest.write_bytes(contents)
                with self.subTest(contents=contents), patch("nomzy.sprites.get_animation_manifest_path", return_value=manifest), self.assertLogs("nomzy.sprites"):
                    assets = load_sprite_assets()
                self.assertFalse(assets.frames[0].isNull())
                CompanionStateMachine(assets.activity_clips)
                player = AnimationPlayer(assets.clips, "pet")
                player.advance(1000)
                self.assertTrue(player.finished)
            with patch("nomzy.sprites._load_sources", side_effect=RuntimeError("bad PNG")), self.assertLogs("nomzy.sprites"):
                self.assertEqual(len(load_sprite_assets().frames), 1)

    def test_invalid_utf8_settings_recover(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_bytes(b"\xff")
            with self.assertLogs("nomzy.storage"):
                self.assertIsNone(read_json_object(path))

    def test_native_initialization_and_status_exceptions_are_nonfatal(self):
        with patch("nomzy.login_item.has_native_macos_windowing", return_value=True), patch("nomzy.login_item.platform.mac_ver", return_value=("", (), "")), self.assertLogs("nomzy.login_item"):
            item = LoginItem()
        self.assertFalse(item.status()[0])
        item.service = Mock()
        item.service.status.side_effect = RuntimeError("native bridge failed")
        with self.assertLogs("nomzy.login_item"):
            self.assertIn("Unable to check", item.status()[1])
        item.service.registerAndReturnError_.side_effect = RuntimeError("native bridge failed")
        with self.assertLogs("nomzy.login_item"), self.assertRaisesRegex(RuntimeError, "Unable to change"):
            item.set_enabled(True)

    def test_shutdown_releases_lock_after_window_cleanup_failure(self):
        controller = ApplicationController(self.app)
        controller.nomzy = Mock()
        controller.nomzy.findChildren.return_value = []
        controller.nomzy.settings_window.close.side_effect = RuntimeError("native close failed")
        controller.lock = Mock()
        with self.assertLogs("nomzy.application"):
            controller.shutdown()
        controller.lock.unlock.assert_called_once()
        controller.nomzy.hide.assert_called_once()
        controller.shutdown()
        controller.deleteLater()

    def test_logs_rotate_and_callback_errors_do_not_use_stderr(self):
        root = logging.getLogger()
        old_handlers, old_level = root.handlers[:], root.level
        old_raise = logging.raiseExceptions
        root.handlers = []
        try:
            with tempfile.TemporaryDirectory() as directory, patch("nomzy.diagnostics.get_log_dir", return_value=Path(directory)), patch("sys.stderr") as stderr:
                configure_logging()
                configure_logging()
                self.assertEqual(len(root.handlers), 1)
                for _ in range(12):
                    logging.getLogger("nomzy.test").info("x" * 100000)
                error = RuntimeError("callback failed")
                log_unhandled_exception(type(error), error, None)
                self.assertIn("callback failed", (Path(directory) / "nomzy.log").read_text())
                self.assertEqual(len(list(Path(directory).glob("nomzy.log*"))), 3)
                stderr.write.assert_not_called()
        finally:
            for handler in root.handlers:
                handler.close()
            root.handlers, root.level = old_handlers, old_level
            logging.raiseExceptions = old_raise

    def test_unwritable_log_directory_is_nonfatal(self):
        root = logging.getLogger()
        old_handlers, old_level = root.handlers[:], root.level
        old_raise = logging.raiseExceptions
        root.handlers = []
        try:
            with patch("nomzy.diagnostics.get_log_dir", side_effect=PermissionError), patch("sys.stderr") as stderr:
                configure_logging()
                logging.error("still running")
                stderr.write.assert_not_called()
        finally:
            for handler in root.handlers:
                handler.close()
            root.handlers, root.level = old_handlers, old_level
            logging.raiseExceptions = old_raise
