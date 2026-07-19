import unittest
from unittest.mock import Mock, call

from nomzy.activity import CompanionState
from nomzy.scheduling import BehaviorAction, BehaviorScheduler


SETTINGS = {
    "walk_interval_seconds": 10,
    "walk_min_ticks": 10,
    "walk_max_ticks": 35,
    "speech_min_ticks": 1500,
    "speech_max_ticks": 4500,
    "speech_min_duration_ticks": 75,
    "speech_max_duration_ticks": 125,
    "blink_min_interval_ms": 6000,
    "blink_max_interval_ms": 12000,
    "rest_min_interval_ms": 45000,
    "rest_max_interval_ms": 120000,
}


def minimum_random():
    rng = Mock()
    rng.randint.side_effect = lambda minimum, maximum: minimum
    return rng


class BehaviorSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.rng = minimum_random()
        self.scheduler = BehaviorScheduler(SETTINGS, rng=self.rng)

    def test_walk_cooldown_uses_natural_variation(self):
        self.assertEqual(self.scheduler.walk_cooldown_ticks, 188)
        self.assertIn(call(188, 312), self.rng.randint.call_args_list)

    def test_walk_schedule_emits_start_then_steps(self):
        self.scheduler.walk_cooldown_ticks = 1

        action = self.scheduler.next_movement_action(
            CompanionState.IDLE,
            enabled=True,
        )

        self.assertEqual(action, BehaviorAction.START_WALKING)
        self.assertEqual(self.scheduler.walk_ticks_remaining, 10)
        self.assertEqual(
            self.scheduler.next_movement_action(
                CompanionState.WALKING,
                enabled=True,
            ),
            BehaviorAction.WALK_STEP,
        )

    def test_walk_duration_finishes_after_its_scheduled_steps(self):
        self.scheduler.walk_ticks_remaining = 2

        self.assertFalse(self.scheduler.complete_walk_step())
        self.assertTrue(self.scheduler.complete_walk_step())

    def test_disabled_movement_does_not_advance_its_cooldown(self):
        self.scheduler.walk_cooldown_ticks = 10

        action = self.scheduler.next_movement_action(
            CompanionState.IDLE,
            enabled=False,
        )

        self.assertIsNone(action)
        self.assertEqual(self.scheduler.walk_cooldown_ticks, 10)

    def test_speech_schedule_emits_speak_and_hide_message(self):
        self.scheduler.speech_cooldown_ticks = 1
        self.assertEqual(
            self.scheduler.next_speech_action(enabled=True),
            BehaviorAction.SPEAK,
        )

        self.scheduler.start_message()
        self.scheduler.message_ticks_remaining = 1
        self.assertEqual(
            self.scheduler.next_speech_action(enabled=True),
            BehaviorAction.HIDE_MESSAGE,
        )

    def test_settings_update_limits_existing_speech_cooldown(self):
        self.scheduler.speech_cooldown_ticks = 4000

        self.scheduler.update_settings(SETTINGS | {"speech_max_ticks": 2000})

        self.assertEqual(self.scheduler.speech_cooldown_ticks, 2000)

    def test_blinking_does_not_pause_rest_countdown(self):
        self.scheduler.rest_cooldown_ms = 100

        action = self.scheduler.next_ambient_action(
            CompanionState.BLINKING,
            elapsed_ms=40,
        )

        self.assertIsNone(action)
        self.assertEqual(self.scheduler.rest_cooldown_ms, 60)

    def test_other_activities_pause_rest_countdown(self):
        self.scheduler.rest_cooldown_ms = 100

        action = self.scheduler.next_ambient_action(
            CompanionState.WALKING,
            elapsed_ms=40,
        )

        self.assertIsNone(action)
        self.assertEqual(self.scheduler.rest_cooldown_ms, 100)

    def test_rest_takes_priority_when_blink_is_also_due(self):
        self.scheduler.rest_cooldown_ms = 1
        self.scheduler.blink_cooldown_ms = 1

        action = self.scheduler.next_ambient_action(
            CompanionState.IDLE,
            elapsed_ms=40,
        )

        self.assertEqual(action, BehaviorAction.REST)
        self.assertEqual(self.scheduler.rest_cooldown_ms, 45000)
        self.assertLessEqual(self.scheduler.blink_cooldown_ms, 0)

    def test_rest_interval_is_between_forty_five_and_one_twenty_seconds(self):
        self.scheduler.rest_cooldown_ms = 1
        self.scheduler.next_ambient_action(CompanionState.IDLE, elapsed_ms=40)

        self.assertIn(call(45000, 120000), self.rng.randint.call_args_list)


if __name__ == "__main__":
    unittest.main()
