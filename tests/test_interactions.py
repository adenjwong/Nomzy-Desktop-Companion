import unittest

from PySide6.QtCore import QPoint

from nomzy.interactions import CompanionInteractionMixin


class InteractionHarness(CompanionInteractionMixin):
    def __init__(self):
        self.is_dragging = False
        self.drag_animation_pending = False
        self.menu_visible = True
        self.movement_state = "walking"
        self.walk_ticks_remaining = 10
        self.walk_step_x = 1
        self.walk_step_y = 1
        self.idle_ticks_remaining = 0
        self.active_reaction = "pet"
        self.ambient_animation = "blink"
        self.drag_direction_x = 100
        self.last_direction = 1
        self.animation_updates = 0
        self.paint_updates = 0

    def random_walk_cooldown_ticks(self):
        return 250

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

        self.assertTrue(harness.is_dragging)
        self.assertTrue(harness.drag_animation_pending)
        self.assertFalse(harness.menu_visible)
        self.assertEqual(harness.movement_state, "idle")
        self.assertEqual(harness.walk_ticks_remaining, 0)
        self.assertEqual(harness.idle_ticks_remaining, 250)
        self.assertIsNone(harness.active_reaction)
        self.assertIsNone(harness.ambient_animation)

    def test_finish_dragging_returns_to_regular_animation(self):
        harness = InteractionHarness()
        harness.is_dragging = True
        harness.drag_animation_pending = True

        harness.finish_dragging()

        self.assertFalse(harness.is_dragging)
        self.assertFalse(harness.drag_animation_pending)
        self.assertEqual(harness.idle_ticks_remaining, 250)
        self.assertEqual(harness.animation_updates, 1)


if __name__ == "__main__":
    unittest.main()
