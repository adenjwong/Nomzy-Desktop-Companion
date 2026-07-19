import unittest

from PySide6.QtCore import QPoint

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
        self.scheduler = BehaviorScheduler({"walk_interval_seconds": 10})
        self.scheduler.start_walk()
        self.walk_step_x = 1
        self.walk_step_y = 1
        self.drag_direction_x = 100
        self.last_direction = 1
        self.animation_updates = 0
        self.paint_updates = 0

    def update_animation(self, elapsed_ms):
        self.animation_updates += 1

    def update_window_size_for_state(self):
        pass

    def update_overlay_mask(self):
        pass

    def update(self):
        self.paint_updates += 1


class DragInteractionTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
