import unittest
from unittest.mock import patch

from PySide6.QtCore import QPoint, QRect, QSize

from nomzy.windowing import CompanionWindowMixin


class FakeScreen:
    def __init__(self, geometry):
        self.geometry = geometry

    def availableGeometry(self):
        return self.geometry


class WindowHarness(CompanionWindowMixin):
    def __init__(self):
        self.settings = {"save_position": True}
        self.last_direction = 1
        self.window_position = QPoint()
        self.window_size = QSize(140, 115)

    def width(self):
        return self.window_size.width()

    def height(self):
        return self.window_size.height()

    def size(self):
        return self.window_size

    def get_scaled_sprite(self):
        return object()

    def get_sprite_rect(self, scaled_sprite, force_message=None, force_menu=None):
        return QRect(10, 20, 100, 80)


class MultiDisplayWindowTests(unittest.TestCase):
    def setUp(self):
        self.left_screen = FakeScreen(QRect(-1920, 0, 1920, 1080))
        self.primary_screen = FakeScreen(QRect(0, 0, 1920, 1080))
        self.screens = [self.left_screen, self.primary_screen]
        self.harness = WindowHarness()

    def screen_patches(self):
        return (
            patch(
                "nomzy.windowing.QApplication.screens",
                return_value=self.screens,
            ),
            patch(
                "nomzy.windowing.QApplication.primaryScreen",
                return_value=self.primary_screen,
            ),
        )

    def test_global_point_selects_the_display_that_contains_it(self):
        screens_patch, primary_patch = self.screen_patches()
        with screens_patch, primary_patch:
            screen = self.harness.get_screen_for_global_point(
                QPoint(-800, 400)
            )

        self.assertIs(screen, self.left_screen)

    def test_saved_position_is_restored_on_its_original_display(self):
        saved_state = {
            "sprite_center_x": -800,
            "sprite_center_y": 400,
            "last_direction": -1,
        }
        screens_patch, primary_patch = self.screen_patches()
        with (
            screens_patch,
            primary_patch,
            patch("nomzy.windowing.load_state", return_value=saved_state),
        ):
            position = self.harness.get_saved_position()

        self.assertEqual(position, QPoint(-859, 341))
        self.assertEqual(self.harness.last_direction, -1)

    def test_disconnected_saved_position_moves_to_nearest_display(self):
        saved_state = {
            "sprite_center_x": 3000,
            "sprite_center_y": 400,
            "last_direction": 1,
        }
        screens_patch, primary_patch = self.screen_patches()
        with (
            screens_patch,
            primary_patch,
            patch("nomzy.windowing.load_state", return_value=saved_state),
        ):
            position = self.harness.get_saved_position()

        self.assertEqual(position, QPoint(1780, 341))

    def test_full_menu_window_is_clamped_inside_current_display(self):
        self.harness.window_size = QSize(360, 300)
        screens_patch, primary_patch = self.screen_patches()
        with screens_patch, primary_patch:
            position = self.harness.clamp_position_to_available_screen(
                -100,
                900,
                reference_point=QPoint(100, 1000),
            )

        self.assertEqual(position, QPoint(0, 780))

    def test_removed_display_schedules_visibility_recovery(self):
        self.harness._tracked_screens = self.screens.copy()

        with patch("nomzy.windowing.QTimer.singleShot") as single_shot:
            self.harness._handle_screen_removed(self.left_screen)

        self.assertEqual(self.harness._tracked_screens, [self.primary_screen])
        single_shot.assert_called_once_with(
            0,
            self.harness.ensure_visible_on_available_screen,
        )


if __name__ == "__main__":
    unittest.main()
