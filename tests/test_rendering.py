import unittest

from PySide6.QtCore import QRect

from nomzy.rendering import CompanionRenderingMixin


class RenderingHarness(CompanionRenderingMixin):
    def __init__(self, direction):
        self.last_direction = direction
        self.message = "hello"


class SpeechBubbleGeometryTests(unittest.TestCase):
    def test_bubble_and_tail_form_one_continuous_shape(self):
        sprite_rect = QRect(140, 80, 110, 85)

        for direction in (-1, 1):
            harness = RenderingHarness(direction)
            bubble_rect, bubble_path = harness.get_speech_bubble_geometry(
                sprite_rect
            )

            self.assertIsNotNone(bubble_rect)
            self.assertEqual(len(bubble_path.toSubpathPolygons()), 1)

    def test_tail_extends_from_bubble_toward_nomzys_mouth(self):
        sprite_rect = QRect(140, 80, 110, 85)

        for direction in (-1, 1):
            harness = RenderingHarness(direction)
            bubble_rect, bubble_path = harness.get_speech_bubble_geometry(
                sprite_rect
            )
            path_bounds = bubble_path.boundingRect()

            if direction < 0:
                self.assertGreater(path_bounds.right(), bubble_rect.right())
            else:
                self.assertLess(path_bounds.left(), bubble_rect.left())

    def test_tail_leaves_clearance_from_nomzys_sprite(self):
        sprite_rect = QRect(140, 80, 110, 85)

        for direction in (-1, 1):
            harness = RenderingHarness(direction)
            mouth = harness.get_mouth_point(sprite_rect)
            tail_tip = harness.get_speech_tail_tip(sprite_rect, mouth)

            if direction < 0:
                self.assertGreaterEqual(sprite_rect.left() - tail_tip.x(), 10)
            else:
                self.assertGreaterEqual(tail_tip.x() - sprite_rect.right(), 10)


if __name__ == "__main__":
    unittest.main()
