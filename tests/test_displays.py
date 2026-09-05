import unittest

from PySide6.QtCore import QPoint, QRect, QSize

from nomzy.displays import (
    clamp_window_position,
    normalized_position,
    position_from_normalized,
    remap_point,
    screen_index_for_point,
)


class DisplayGeometryTests(unittest.TestCase):
    def setUp(self):
        self.geometries = [
            QRect(-1920, 0, 1920, 1080),
            QRect(0, 0, 2560, 1440),
            QRect(0, -900, 1600, 900),
            QRect(2560, 0, 1512, 982),
            QRect(0, 1440, 1920, 1080),
        ]

    def test_screen_is_selected_from_negative_coordinates(self):
        self.assertEqual(
            screen_index_for_point(self.geometries, QPoint(-500, 300)),
            0,
        )

    def test_screen_is_selected_above_the_primary_display(self):
        self.assertEqual(
            screen_index_for_point(self.geometries, QPoint(500, -400)),
            2,
        )

    def test_screens_are_selected_right_and_below_the_primary_display(self):
        self.assertEqual(
            screen_index_for_point(self.geometries, QPoint(3000, 500)),
            3,
        )
        self.assertEqual(
            screen_index_for_point(self.geometries, QPoint(500, 1800)),
            4,
        )

    def test_scaled_display_geometry_uses_qt_logical_coordinates(self):
        scaled_display = self.geometries[3]
        position = clamp_window_position(
            QPoint(4000, 900),
            QSize(360, 190),
            scaled_display,
        )

        self.assertEqual(position, QPoint(3712, 792))

    def test_nearest_screen_is_selected_for_a_disconnected_position(self):
        remaining_geometries = self.geometries[:2]

        self.assertEqual(
            screen_index_for_point(
                remaining_geometries,
                QPoint(500, -400),
            ),
            1,
        )

    def test_window_is_clamped_inside_a_negative_origin_display(self):
        position = clamp_window_position(
            QPoint(-2100, 1200),
            QSize(360, 190),
            self.geometries[0],
        )

        self.assertEqual(position, QPoint(-1920, 890))

    def test_window_can_reach_the_last_pixel_of_a_display(self):
        position = clamp_window_position(
            QPoint(3000, 2000),
            QSize(360, 190),
            self.geometries[1],
        )

        self.assertEqual(position, QPoint(2200, 1250))

    def test_no_screen_is_selected_when_none_are_available(self):
        self.assertIsNone(screen_index_for_point([], QPoint()))

    def test_relative_position_survives_coordinate_and_scale_changes(self):
        old_geometry = QRect(-1920, 0, 1920, 1080)
        new_geometry = QRect(1512, -982, 2560, 1440)
        old_point = QPoint(-960, 540)

        remapped = remap_point(old_point, old_geometry, new_geometry)
        relative = normalized_position(old_point, old_geometry)

        self.assertEqual(
            remapped,
            position_from_normalized(*relative, new_geometry),
        )
        self.assertTrue(new_geometry.contains(remapped))


if __name__ == "__main__":
    unittest.main()
