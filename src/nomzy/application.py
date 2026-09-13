"""Application lifetime and controls independent of the companion's sprite."""
import logging
import signal

from PySide6.QtCore import QObject, QLockFile, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QCursor
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import __version__
from .about_window import AboutWindow
from .companion import NomzyDog
from .macos_overlay import configure_macos_application
from .paths import APPLICATION_NAME, ORGANIZATION_NAME, get_user_data_dir

LOGGER = logging.getLogger(__name__)


class ApplicationController(QObject):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.nomzy = None
        self.tray = None
        self.lock = None
        self.stopped = False
        self.previous_signals = {}
        self.about_window = None
        app.setOrganizationName(ORGANIZATION_NAME)
        app.setApplicationName(APPLICATION_NAME)
        app.setApplicationDisplayName("Nomzy")
        app.setApplicationVersion(__version__)
        app.setQuitOnLastWindowClosed(False)
        app.aboutToQuit.connect(self.shutdown)
        app.commitDataRequest.connect(lambda manager: self.save_state())

    def start(self):
        directory = get_user_data_dir()
        directory.mkdir(parents=True, exist_ok=True)
        self.lock = QLockFile(str(directory / "application.lock"))
        # A long-running live process must never become stale based on age.
        self.lock.setStaleLockTime(0)
        if not self.lock.tryLock(0):
            if self.lock.error() != QLockFile.LockError.LockFailedError:
                raise RuntimeError("Could not acquire Nomzy's application lock.")
            LOGGER.info("Nomzy is already running; use its menu-bar item.")
            return False
        self.nomzy = NomzyDog()
        configure_macos_application(hide_dock_icon=bool(self.nomzy.settings.get("macos_hide_dock_icon", True)))
        self.create_menu_bar()
        position = self.nomzy.get_saved_position()
        if position is None:
            position = self.nomzy.get_centered_position()
        if position is not None:
            self.nomzy.move(position)
        self.nomzy.show()
        for sig in (signal.SIGINT, signal.SIGTERM):
            self.previous_signals[sig] = signal.getsignal(sig)
            signal.signal(sig, lambda *_: self.app.quit())
        # Let Python process termination signals while Qt owns the event loop.
        self.signal_timer = QTimer(self)
        self.signal_timer.timeout.connect(lambda: None)
        self.signal_timer.start(250)
        return True

    def create_menu_bar(self):
        self.menu = QMenu()
        self.menu.addAction("Show / Locate Nomzy", self.locate)
        self.pause_action = self.menu.addAction("Pause Nomzy", self.nomzy.toggle_pause)
        self.menu.addAction("Settings…", self.nomzy.open_settings_window)
        self.menu.addAction("Reset Position", self.reset_position)
        self.menu.addSeparator()
        self.menu.addAction("About Nomzy", self.show_about)
        self.menu.addAction("Quit Nomzy", self.app.quit)
        self.menu.aboutToShow.connect(self.refresh_menu)
        pixmap = QPixmap(27, 27)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.scale(1.2, 1.2)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor("transparent"))
        painter.setBrush(QColor("black"))
        painter.drawEllipse(4, 9, 15, 12)
        for x, y in ((2, 6), (7, 2), (13, 2), (18, 6)):
            painter.drawEllipse(x, y, 4, 6)
        painter.end()
        icon = QIcon(pixmap)
        icon.setIsMask(True)
        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("Nomzy")
        self.tray.setContextMenu(self.menu)
        self.tray.show()

    def refresh_menu(self):
        self.pause_action.setText("Resume Nomzy" if self.nomzy.activity.paused else "Pause Nomzy")

    def locate(self):
        self.nomzy.close_menu()
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        position = self.nomzy.get_centered_position(screen)
        if position is not None:
            self.nomzy.move(position)
        self.nomzy.show()
        self.nomzy.raise_()

    def reset_position(self):
        self.nomzy.close_menu()
        self.nomzy.reset_position()
        self.nomzy.show()
        self.save_state()

    def show_about(self):
        if self.about_window is None:
            self.about_window = AboutWindow(self.nomzy.get_scaled_sprite())
        self.about_window.present()

    def save_state(self):
        if self.nomzy is not None:
            try:
                self.nomzy.save_state()
            except Exception:
                LOGGER.exception("Could not save Nomzy's position")

    def shutdown(self):
        if self.stopped:
            return
        self.stopped = True
        self.save_state()
        if self.nomzy is not None:
            for timer in self.nomzy.findChildren(QTimer):
                timer.stop()
            if self.nomzy.settings_window is not None:
                self.nomzy.settings_window.close()
            self.nomzy.hide()
        if self.about_window is not None:
            self.about_window.close()
        if self.tray is not None:
            self.tray.hide()
            self.menu.close()
        if hasattr(self, "signal_timer"):
            self.signal_timer.stop()
        for sig, handler in self.previous_signals.items():
            signal.signal(sig, handler)
        if self.lock is not None and self.lock.isLocked():
            self.lock.unlock()
