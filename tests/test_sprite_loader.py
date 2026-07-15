import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication, QRegion

from nomzy.sprites import load_sprite_assets


class SpriteLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])
        cls.assets = load_sprite_assets()

    def test_all_source_frames_load(self):
        self.assertEqual(len(self.assets.frames), 23)
        self.assertTrue(all(not frame.isNull() for frame in self.assets.frames))

    def test_frames_are_trimmed_to_visible_pixels(self):
        for frame in self.assets.frames:
            self.assertEqual(QRegion(frame.mask()).boundingRect(), frame.rect())

    def test_rest_clips_are_available(self):
        self.assertIn("sit", self.assets.clips)
        self.assertIn("sleep", self.assets.clips)

    def test_drag_clip_is_available(self):
        self.assertIn("drag", self.assets.clips)
        self.assertEqual(self.assets.clips["drag"].render_scale, 1.2)


if __name__ == "__main__":
    unittest.main()
