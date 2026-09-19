"""Exercise a separate app's native full-screen Space and return to the desktop.

Uses temporary settings/state and Nomzy's real single-instance lock. This opens
one disposable test app; it never changes another app's documents or windows.
"""
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import AppKit
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel

from nomzy.application import ApplicationController
from nomzy.macos_overlay import get_ns_window, has_native_macos_windowing
from nomzy.settings import DEFAULT_SETTINGS


def wait_until(predicate, description, timeout=10000):
    for _ in range(timeout // 100):
        if predicate():
            return
        QTest.qWait(100)
    raise AssertionError(description)


def fullscreen_fixture(root):
    app = QApplication([])
    window = QLabel('Nomzy full-screen verification — closes automatically')
    window.setWindowTitle('Nomzy full-screen test app')
    window.resize(800, 500)
    window.show()
    native = get_ns_window(window)
    native.setCollectionBehavior_(AppKit.NSWindowCollectionBehaviorFullScreenPrimary)
    AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    native.makeKeyAndOrderFront_(None)
    QTimer.singleShot(500, lambda: native.toggleFullScreen_(None))

    def poll():
        if (native.styleMask() & AppKit.NSWindowStyleMaskFullScreen
                and native.isOnActiveSpace()):
            (root / 'fullscreen').touch()
            (root / 'active').touch()
        else:
            (root / 'active').unlink(missing_ok=True)
        if (root / 'stop').exists():
            app.quit()
    timer = QTimer()
    timer.timeout.connect(poll)
    timer.start(100)
    QTimer.singleShot(30000, app.quit)
    app.exec()


def verify():
    app = QApplication([])
    if not has_native_macos_windowing():
        raise SystemExit('Native Spaces checks require the Cocoa backend.')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        with patch('nomzy.companion.load_settings', return_value=DEFAULT_SETTINGS | {
            'movement_enabled': False, 'speech_enabled': False,
        }), patch('nomzy.state.get_state_path', return_value=root / 'state.json'), \
                patch('nomzy.state.get_legacy_state_path', return_value=root / 'missing.json'):
            controller = ApplicationController(app)
            process = None
            try:
                if not controller.start():
                    print('SKIPPED: Quit the running Nomzy before native Spaces testing.')
                    return
                QTest.qWait(500)
                overlay = get_ns_window(controller.nomzy)
                assert overlay.isOnActiveSpace()
                process = subprocess.Popen([sys.executable, __file__, '--fixture', str(root)])
                wait_until(lambda: (root / 'fullscreen').exists(), 'Fixture failed to enter full screen')
                QTest.qWait(1500)
                assert overlay.isOnActiveSpace(), 'Overlay did not follow the full-screen Space'
                assert overlay.isVisible()
                assert overlay.level() == AppKit.NSStatusWindowLevel
                assert not overlay.isKeyWindow()
                front = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
                assert front.processIdentifier() == process.pid, 'Fixture is not the foreground app'
                controller.nomzy.toggle_pause()
                controller.locate()
                QTest.qWait(300)
                assert controller.nomzy.activity.paused
                assert AppKit.NSWorkspace.sharedWorkspace().frontmostApplication().processIdentifier() == process.pid
                controller.show_settings()
                QTest.qWait(500)
                settings = get_ns_window(controller.nomzy.settings_window)
                assert settings.isOnActiveSpace() and settings.isKeyWindow()
                assert (root / 'active').exists(), 'Settings switched away from the full-screen Space'
                assert overlay.isOnActiveSpace()
                controller.nomzy.settings_window.close()
                print('PASS: overlay and paused Locate in a separate app full-screen Space; Settings takes focus', flush=True)
                (root / 'stop').touch()
                wait_until(lambda: process.poll() is not None, 'Fixture failed to exit')
                QTest.qWait(1200)
                assert overlay.isOnActiveSpace() and overlay.isVisible()
                controller.show_settings()
                QTest.qWait(300)
                assert get_ns_window(controller.nomzy.settings_window).isKeyWindow()
                print('PASS: overlay and Settings recover after full-screen Space closes', flush=True)
            finally:
                if process is not None and process.poll() is None:
                    (root / 'stop').touch()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait(timeout=3)
                controller.shutdown()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--fixture':
        fullscreen_fixture(Path(sys.argv[2]))
    else:
        verify()
