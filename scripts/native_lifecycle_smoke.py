"""Run on a macOS desktop; briefly activates test windows, using temporary state."""
import tempfile
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from nomzy.application import ApplicationController
from nomzy.macos_overlay import get_ns_window
from nomzy.settings import DEFAULT_SETTINGS

app = QApplication([])
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    with patch('nomzy.companion.load_settings', return_value=dict(DEFAULT_SETTINGS)), \
         patch('nomzy.state.get_state_path', return_value=root / 'state.json'), \
         patch('nomzy.state.get_legacy_state_path', return_value=root / 'missing.json'):
        controller = ApplicationController(app)
        if not controller.start():
            controller.shutdown()
            print('SKIPPED: Nomzy is already running. Quit it before running the native smoke test.', flush=True)
            raise SystemExit(0)
        failures = []
        def check():
            try:
                assert QSystemTrayIcon.isSystemTrayAvailable()
                assert controller.tray.isVisible()
                controller.nomzy.open_settings_window()
                app.processEvents()
                assert get_ns_window(controller.nomzy.settings_window).isKeyWindow()
                controller.nomzy.settings_window.close()
                assert controller.nomzy.isVisible()
                controller.nomzy.toggle_pause()
                controller.refresh_menu()
                assert controller.pause_action.text() == 'Resume Nomzy'
                controller.locate()
                controller.reset_position()
                import AppKit
                visible_before = {int(w.windowNumber()) for w in AppKit.NSApplication.sharedApplication().windows() if w.isVisible()}
                controller.show_about()
                app.processEvents()
                assert get_ns_window(controller.about_window).isKeyWindow()
                visible_after = {int(w.windowNumber()) for w in AppKit.NSApplication.sharedApplication().windows() if w.isVisible()}
                assert len(visible_after - visible_before) == 1, 'About must create exactly one visible native window'
                controller.about_window.accept()
                app.processEvents()
                assert not controller.about_window.isVisible()
                controller.show_about()
                app.processEvents()
                assert get_ns_window(controller.about_window).isKeyWindow()
                print('PASS: native tray, Settings and About activation, close, pause, locate, reset', flush=True)
            except Exception as error:
                failures.append(error)
            finally:
                app.quit()
        QTimer.singleShot(600, check)
        app.exec()
        controller.shutdown()
        assert (root / 'state.json').is_file()
        assert not controller.lock.isLocked()
        if failures:
            raise failures[0]
        print('PASS: native shutdown saved position and released lock', flush=True)
