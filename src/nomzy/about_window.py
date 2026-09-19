"""A single Qt-owned About window, avoiding Cocoa's native alert proxy."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from . import __version__
from .macos_overlay import activate_settings_window


class AboutWindow(QDialog):
    def __init__(self, sprite):
        super().__init__()
        self.setWindowTitle("About Nomzy")
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setFixedWidth(320)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        artwork = QLabel()
        artwork.setPixmap(sprite)
        artwork.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(artwork)
        title = QLabel(f"Nomzy {__version__}")
        font = title.font()
        font.setBold(True)
        font.setPointSize(16)
        title.setFont(font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        description = QLabel("Your desktop companion.\n\nUse the menu-bar paw to locate, pause, or configure Nomzy.")
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(description)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.buttons.accepted.connect(self.accept)
        layout.addWidget(self.buttons)

    def present(self):
        from .macos_overlay import prepare_settings_window
        prepare_settings_window(self)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        activate_settings_window(self)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setFocus()
