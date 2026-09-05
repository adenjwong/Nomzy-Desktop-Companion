import unittest
from unittest.mock import patch

from PySide6.QtCore import QPoint, QRect, QSize

from nomzy.windowing import CompanionWindowMixin


class FakeScreen:
    def __init__(self, geometry, name="Display", serial=""):
        self.geometry = geometry
        self.screen_name = name
        self.serial = serial

    def availableGeometry(self):
        return self.geometry

    def name(self):
        return self.screen_name

    def manufacturer(self):
        return "Test"

    def model(self):
        return self.screen_name

    def serialNumber(self):
        return self.serial


class WindowHarness(CompanionWindowMixin):
    def __init__(self):
        self.settings = {"save_position": True}
        self.last_direction = 1
        self.window_position = QPoint()
        self.window_size = QSize(140, 115)
        self.message = ""
        self._screen_geometries = {}
        self._display_recovery_pending = False
        self._pending_sprite_center = None
        self._pending_recovery_screen = None

    def width(self):
        return self.window_size.width()

    def height(self):
        return self.window_size.height()

    def size(self):
        return self.window_size

    def pos(self):
        return self.window_position

    def x(self):
        return self.window_position.x()

    def y(self):
        return self.window_position.y()

    def move(self, *args):
        if len(args) == 1:
            self.window_position = QPoint(args[0])
        else:
            self.window_position = QPoint(*args)

    def mapToGlobal(self, point):
        return self.window_position + point

    def get_scaled_sprite(self):
        return object()

    def get_sprite_rect(self, scaled_sprite, force_message=None, force_menu=None):
        return QRect(10, 20, 100, 80)


class MultiDisplayWindowTests(unittest.TestCase):
    def setUp(self):
        self.left_screen = FakeScreen(
            QRect(-1920, 0, 1920, 1080),
            name="Left",
            serial="LEFT-1",
        )
        self.primary_screen = FakeScreen(
            QRect(0, 0, 1920, 1080),
            name="Primary",
            serial="PRIMARY-1",
        )
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

    def test_initial_position_centers_the_sprite_not_the_window(self):
        screens_patch, primary_patch = self.screen_patches()
        with screens_patch, primary_patch:
            position = self.harness.get_centered_position()

        sprite_center = position + self.harness.get_sprite_rect(object()).center()
        self.assertEqual(sprite_center, self.primary_screen.geometry.center())

    def test_saved_relative_position_follows_a_rearranged_display(self):
        moved_screen = FakeScreen(
            QRect(1920, -200, 2560, 1440),
            name="Left",
            serial="LEFT-1",
        )
        saved_state = {
            "sprite_center_x": -800,
            "sprite_center_y": 400,
            "last_direction": -1,
            "screen_id": "serial:LEFT-1",
            "screen_relative_x": 0.5,
            "screen_relative_y": 0.25,
        }
        self.screens = [self.primary_screen, moved_screen]
        screens_patch, primary_patch = self.screen_patches()
        with (
            screens_patch,
            primary_patch,
            patch("nomzy.windowing.load_state", return_value=saved_state),
        ):
            position = self.harness.get_saved_position()

        sprite_center = position + self.harness.get_sprite_rect(object()).center()
        self.assertEqual(sprite_center, QPoint(3200, 160))

    def test_save_records_absolute_and_display_relative_positions(self):
        self.harness.window_position = QPoint(-859, 341)
        screens_patch, primary_patch = self.screen_patches()

        with screens_patch, primary_patch, patch(
            "nomzy.windowing.write_state"
        ) as write_state:
            self.harness.save_state()

        state = write_state.call_args.args[0]
        self.assertEqual(state["sprite_center_x"], -800)
        self.assertEqual(state["sprite_center_y"], 400)
        self.assertEqual(state["screen_id"], "serial:LEFT-1")
        self.assertAlmostEqual(state["screen_relative_x"], 1120 / 1919)
        self.assertAlmostEqual(state["screen_relative_y"], 400 / 1079)

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
            self.harness._finish_display_recovery,
        )

    def test_coordinate_rearrangement_preserves_relative_sprite_position(self):
        old_geometry = QRect(-1920, 0, 1920, 1080)
        new_geometry = QRect(0, -1080, 1920, 1080)
        self.left_screen.geometry = new_geometry
        self.harness._screen_geometries[id(self.left_screen)] = old_geometry
        self.harness.window_position = QPoint(-1019, 481)
        screens_patch, primary_patch = self.screen_patches()

        with screens_patch, primary_patch, patch(
            "nomzy.windowing.QTimer.singleShot"
        ):
            self.harness._handle_screen_geometry_changed(
                self.left_screen,
                new_geometry,
            )
            self.harness._finish_display_recovery()

        self.assertEqual(
            self.harness.get_sprite_global_center(),
            QPoint(960, -540),
        )

    def test_recovery_keeps_every_overlay_size_reachable(self):
        self.screens = [self.primary_screen]
        screens_patch, primary_patch = self.screen_patches()

        with screens_patch, primary_patch:
            for size in (
                QSize(140, 115),
                QSize(360, 190),
                QSize(360, 300),
            ):
                with self.subTest(size=size):
                    self.harness.window_size = size
                    self.harness.window_position = QPoint(-4000, 3000)
                    self.harness.ensure_visible_on_available_screen()
                    window_rect = QRect(self.harness.pos(), size)
                    self.assertTrue(
                        self.primary_screen.availableGeometry().contains(
                            window_rect
                        )
                    )


if __name__ == "__main__":
    unittest.main()
