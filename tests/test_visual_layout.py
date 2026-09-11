import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication
from nomzy.companion import NomzyDog
from nomzy.settings import DEFAULT_SETTINGS


class VisualLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        with patch("nomzy.companion.load_settings", return_value=dict(DEFAULT_SETTINGS)):
            self.dog = NomzyDog()
        self.addCleanup(self.dog.deleteLater)

    def test_menu_fits_all_sprite_sizes_and_larger_fonts(self):
        self.dog.activity.menu_open = True
        for scale in (1, 1.5, 2):
            font = QFont(self.app.font())
            font.setPointSizeF(font.pointSizeF() * scale)
            self.dog.setFont(font)
            for width in range(60, 181):
                self.dog.settings.update(sprite_width=width, sprite_height=round(width * 85 / 110))
                self.dog.update_window_size_for_state()
                buttons = self.dog.get_menu_buttons(self.dog.get_sprite_rect(self.dog.get_scaled_sprite()))
                for index, button in enumerate(buttons):
                    rect = button["rect"]
                    self.assertTrue(self.dog.rect().contains(rect))
                    self.assertLess(QFontMetrics(font).horizontalAdvance(button["label"]) + 16, rect.width())
                    for other in buttons[index + 1:]:
                        delta = rect.center() - other["rect"].center()
                        self.assertGreater(delta.x() ** 2 + delta.y() ** 2, rect.width() ** 2)

    def test_long_speech_fits_both_directions(self):
        font = QFont(self.app.font())
        font.setPointSizeF(font.pointSizeF() * 2)
        self.dog.setFont(font)
        self.dog.message = "good job, " + "W" * 80 + "!"
        for width in (60, 110, 180):
            self.dog.settings.update(sprite_width=width, sprite_height=round(width * 85 / 110))
            for direction in (-1, 1):
                self.dog.last_direction = direction
                self.dog.update_window_size_for_state()
                _, path = self.dog.get_speech_bubble_geometry(self.dog.get_sprite_rect(self.dog.get_scaled_sprite()))
                self.assertTrue(self.dog.rect().contains(path.boundingRect().toAlignedRect()))
