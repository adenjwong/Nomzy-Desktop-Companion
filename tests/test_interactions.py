import unittest

from PySide6.QtWidgets import QApplication

from PySide6.QtCore import QPoint, QRect

from nomzy.activity import (
    CompanionActivityMixin,
    CompanionEvent,
    CompanionState,
    CompanionStateMachine,
)
from nomzy.interactions import CompanionInteractionMixin
from nomzy.scheduling import BehaviorScheduler


ACTIVITY_CLIPS = {
    CompanionState.IDLE: "idle",
    CompanionState.WALKING: "walk",
    CompanionState.BLINKING: "blink",
    CompanionState.SITTING: "sit",
    CompanionState.SLEEPING: "sleep",
    CompanionState.TALKING: "talk",
    CompanionState.DRAGGING: "drag",
    CompanionState.PAUSED: "paused",
    CompanionState.MENU: "paused",
}


class InteractionHarness(CompanionActivityMixin, CompanionInteractionMixin):
    def __init__(self):
        self.activity = CompanionStateMachine(ACTIVITY_CLIPS)
        self.activity.menu_open = True
        self.activity.state = CompanionState.MENU
        self.settings = {
            "menu_arc_radius": 102,
            "menu_button_radius": 24,
        }
        self.scheduler = BehaviorScheduler({"walk_interval_seconds": 10})
        self.scheduler.start_walk()
        self.walk_step_x = 1
        self.walk_step_y = 1
        self.drag_direction_x = 100
        self.drag_pointer_offset = QPoint()
        self.last_direction = 1
        self.animation_updates = 0
        self.paint_updates = 0
        self.visibility_checks = 0

    def update_animation(self, elapsed_ms):
        self.animation_updates += 1

    def update_window_size_for_state(self):
        pass

    def update_overlay_mask(self):
        pass

    def ensure_visible_on_available_screen(self):
        self.visibility_checks += 1

    def update(self):
        self.paint_updates += 1

    def get_drag_anchor_point(self):
        return QPoint(50, 30)


class DragInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_dragging_left_turns_nomzy_left(self):
        harness = InteractionHarness()

        harness.update_drag_direction(QPoint(95, 100))

        self.assertEqual(harness.last_direction, -1)
        self.assertEqual(harness.drag_direction_x, 95)

    def test_small_horizontal_jitter_does_not_turn_nomzy(self):
        harness = InteractionHarness()

        harness.update_drag_direction(QPoint(98, 100))

        self.assertEqual(harness.last_direction, 1)
        self.assertEqual(harness.drag_direction_x, 100)

    def test_begin_dragging_stops_autonomous_behavior(self):
        harness = InteractionHarness()

        harness.begin_dragging()

        self.assertEqual(harness.activity.state, CompanionState.DRAGGING)
        self.assertFalse(harness.activity.menu_open)
        self.assertEqual(harness.scheduler.walk_ticks_remaining, 0)
        self.assertGreaterEqual(harness.scheduler.walk_cooldown_ticks, 188)
        self.assertLessEqual(harness.scheduler.walk_cooldown_ticks, 312)

    def test_finish_dragging_returns_to_regular_animation(self):
        harness = InteractionHarness()
        harness.activity.dispatch(CompanionEvent.START_DRAGGING)

        harness.finish_dragging()

        self.assertEqual(harness.activity.state, CompanionState.IDLE)
        self.assertEqual(harness.animation_updates, 1)
        self.assertEqual(harness.visibility_checks, 1)

    def test_drag_pointer_offset_prevents_a_jump_at_drag_start(self):
        harness = InteractionHarness()
        harness.drag_pointer_offset = QPoint(12, -4)

        position = harness.get_drag_window_position(QPoint(500, 300))

        self.assertEqual(position, QPoint(438, 274))

    def test_radial_menu_buttons_fit_inside_the_menu_window(self):
        harness = InteractionHarness()
        radius, button_radius = harness.menu_metrics()
        extent = 2 * (radius + button_radius + 8)
        menu_bounds = QRect(0, 0, extent, extent)
        sprite_rect = QRect(extent // 2 - 55, extent // 2 - 42, 110, 85)

        for button in harness.get_menu_buttons(sprite_rect):
            with self.subTest(action=button["action"]):
                self.assertTrue(menu_bounds.contains(button["rect"]))


if __name__ == "__main__":
    unittest.main()
