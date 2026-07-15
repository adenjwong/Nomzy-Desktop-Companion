import unittest
from unittest.mock import patch

from nomzy.animation import AnimationClip, AnimationFrame, AnimationPlayer
from nomzy.behavior import CompanionBehaviorMixin


def one_frame_clip(name):
    return AnimationClip(
        name=name,
        frames=(AnimationFrame(sprite=0, duration_ms=100),),
        loop=name in {"idle", "walk", "paused"},
    )


class BehaviorHarness(CompanionBehaviorMixin):
    def __init__(self):
        self.settings = {
            "walk_interval_seconds": 10,
            "rest_min_interval_ms": 45000,
            "rest_max_interval_ms": 120000,
            "sleep_chance_percent": 30,
        }
        self.movement_state = "idle"
        self.idle_ticks_remaining = 10
        self.walk_ticks_remaining = 0
        self.walk_step_x = 0
        self.walk_step_y = 0
        self.ambient_animation = None
        self.active_reaction = None
        self.paused = False
        self.menu_visible = False
        self.message = ""
        self.talk_animation_pending = False
        self.is_dragging = False
        self.drag_animation_pending = False
        self.blink_cooldown_ms = 5000
        self.rest_cooldown_ms = 5000
        clips = {
            name: one_frame_clip(name)
            for name in ("idle", "blink", "sit", "sleep", "drag", "paused")
        }
        self.animation_player = AnimationPlayer(clips, "idle")


class RestBehaviorTests(unittest.TestCase):
    def test_walk_interval_has_small_natural_variation(self):
        harness = BehaviorHarness()

        with patch("nomzy.behavior.random.randint", return_value=250) as randint:
            cooldown = harness.random_walk_cooldown_ticks()

        self.assertEqual(cooldown, 250)
        randint.assert_called_once_with(188, 312)

    def test_sitting_and_sleeping_pause_the_walk_countdown(self):
        harness = BehaviorHarness()

        for animation in ("sit", "sleep"):
            harness.ambient_animation = animation
            harness.update_movement()
            self.assertEqual(harness.idle_ticks_remaining, 10)

    def test_dragging_pauses_movement_and_plays_drag_animation(self):
        harness = BehaviorHarness()
        harness.is_dragging = True
        harness.drag_animation_pending = True

        harness.update_movement()
        harness.update_animation(0)

        self.assertEqual(harness.idle_ticks_remaining, 10)
        self.assertEqual(harness.animation_player.clip_name, "drag")
        self.assertFalse(harness.drag_animation_pending)

    def test_rest_animation_starts_when_its_cooldown_expires(self):
        harness = BehaviorHarness()
        harness.rest_cooldown_ms = 1

        with (
            patch.object(harness, "choose_rest_animation", return_value="sit"),
            patch.object(harness, "random_rest_cooldown", return_value=60000),
        ):
            harness.update_animation(40)

        self.assertEqual(harness.ambient_animation, "sit")
        self.assertEqual(harness.animation_player.clip_name, "sit")
        self.assertEqual(harness.rest_cooldown_ms, 60000)

    def test_rest_takes_priority_when_blink_is_also_due(self):
        harness = BehaviorHarness()
        harness.blink_cooldown_ms = 1
        harness.rest_cooldown_ms = 1

        with (
            patch.object(harness, "choose_rest_animation", return_value="sleep"),
            patch.object(harness, "random_rest_cooldown", return_value=60000),
        ):
            harness.update_animation(40)

        self.assertEqual(harness.ambient_animation, "sleep")

    def test_sleep_chance_is_clamped(self):
        harness = BehaviorHarness()

        harness.settings["sleep_chance_percent"] = -10
        self.assertEqual(harness.choose_rest_animation(), "sit")

        harness.settings["sleep_chance_percent"] = 110
        self.assertEqual(harness.choose_rest_animation(), "sleep")


if __name__ == "__main__":
    unittest.main()
