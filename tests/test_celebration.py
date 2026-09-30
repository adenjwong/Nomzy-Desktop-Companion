import os
import unittest
from datetime import date, timedelta
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from nomzy.animation import AnimationPlayer
from nomzy.celebration import is_party_day, with_party_hat
from nomzy.rendering import CompanionRenderingMixin
from nomzy.sprites import load_sprite_assets


class CelebrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.assets = load_sprite_assets()

    def test_only_september_29_including_leap_years(self):
        for year in (2026, 2027, 2028):
            day = date(year, 1, 1)
            while day.year == year:
                self.assertEqual(is_party_day(day), day == date(year, 9, 29))
                day += timedelta(days=1)

    def test_running_companion_switches_both_midnights(self):
        harness = CompanionRenderingMixin()
        harness.settings = {"sprite_width": 110, "sprite_height": 100}
        harness.sprite_frames = self.assets.frames
        harness.animation_player = AnimationPlayer(self.assets.clips, "idle")
        with patch("nomzy.celebration.date") as clock:
            clock.today.return_value = date(2026, 9, 28)
            normal = harness.get_scaled_sprite().toImage()
            clock.today.return_value = date(2026, 9, 29)
            party = harness.get_scaled_sprite().toImage()
            self.assertNotEqual(party, normal)
            clock.today.return_value = date(2026, 9, 30)
            self.assertEqual(harness.get_scaled_sprite().toImage(), normal)

    def test_every_pose_preserves_body_size_and_feet(self):
        for source in self.assets.frames:
            sprite = source.scaled(110, 100, Qt.AspectRatioMode.KeepAspectRatio)
            party = with_party_hat(sprite, source)
            padding = party.height() - sprite.height()
            self.assertEqual(party.width(), sprite.width())
            self.assertGreater(padding, 0)
            # The hat must never modify the lower half of the dog's artwork.
            y = sprite.height() // 2
            self.assertEqual(
                party.copy(0, padding + y, sprite.width(), sprite.height() - y).toImage(),
                sprite.copy(0, y, sprite.width(), sprite.height() - y).toImage(),
            )


if __name__ == "__main__":
    unittest.main()
