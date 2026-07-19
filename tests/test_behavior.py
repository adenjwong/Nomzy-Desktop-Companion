import unittest
from unittest.mock import patch

from nomzy.activity import (
    CompanionActivityMixin,
    CompanionEvent,
    CompanionState,
    CompanionStateMachine,
)
from nomzy.animation import (
    AnimationClip,
    AnimationFrame,
    AnimationPlayback,
    AnimationPlayer,
)
from nomzy.behavior import CompanionBehaviorMixin
from nomzy.scheduling import BehaviorAction, BehaviorScheduler


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


def one_frame_clip(name):
    playback = (
        AnimationPlayback.LOOP
        if name in {"idle", "walk", "paused"}
        else AnimationPlayback.RETURN
    )
    return AnimationClip(
        name=name,
        frames=(AnimationFrame(sprite=0, duration_ms=100),),
        playback=playback,
    )


class BehaviorHarness(CompanionActivityMixin, CompanionBehaviorMixin):
    def __init__(self):
        self.settings = {
            "walk_interval_seconds": 10,
            "walk_min_ticks": 10,
            "walk_max_ticks": 35,
            "rest_min_interval_ms": 45000,
            "rest_max_interval_ms": 120000,
            "sleep_chance_percent": 30,
        }
        self.activity = CompanionStateMachine(ACTIVITY_CLIPS)
        self.scheduler = BehaviorScheduler(self.settings)
        self.walk_step_x = 0
        self.walk_step_y = 0
        self.message = ""
        clips = {
            name: one_frame_clip(name)
            for name in (
                "idle",
                "walk",
                "blink",
                "sit",
                "sleep",
                "talk",
                "pet",
                "drag",
                "paused",
            )
        }
        self.animation_player = AnimationPlayer(clips, "idle")


class BehaviorExecutionTests(unittest.TestCase):
    def test_dragging_cancels_scheduled_walk_and_plays_drag_animation(self):
        harness = BehaviorHarness()
        harness.activity.dispatch(CompanionEvent.START_WALKING)
        harness.scheduler.start_walk()

        harness.transition_activity(CompanionEvent.START_DRAGGING)
        harness.update_animation(0)

        self.assertEqual(harness.scheduler.walk_ticks_remaining, 0)
        self.assertEqual(harness.animation_player.clip_name, "drag")

    def test_scheduled_rest_action_starts_selected_animation(self):
        harness = BehaviorHarness()

        with patch.object(harness, "choose_rest_animation", return_value="sit"):
            harness.perform_scheduled_action(BehaviorAction.REST)
            harness.update_animation(0)

        self.assertEqual(harness.activity.state, CompanionState.SITTING)
        self.assertEqual(harness.animation_player.clip_name, "sit")

    def test_scheduled_blink_action_starts_blinking(self):
        harness = BehaviorHarness()

        harness.perform_scheduled_action(BehaviorAction.BLINK)
        harness.update_animation(0)

        self.assertEqual(harness.activity.state, CompanionState.BLINKING)
        self.assertEqual(harness.animation_player.clip_name, "blink")

    def test_hide_message_action_clears_speech_state(self):
        harness = BehaviorHarness()
        harness.message = "hello"
        harness.activity.dispatch(CompanionEvent.START_TALKING)
        harness.scheduler.message_ticks_remaining = 1

        harness.perform_scheduled_action(BehaviorAction.HIDE_MESSAGE)

        self.assertEqual(harness.message, "")
        self.assertEqual(harness.scheduler.message_ticks_remaining, 0)
        self.assertEqual(harness.activity.state, CompanionState.IDLE)

    def test_sleep_chance_is_clamped(self):
        harness = BehaviorHarness()

        harness.settings["sleep_chance_percent"] = -10
        self.assertEqual(harness.choose_rest_animation(), "sit")

        harness.settings["sleep_chance_percent"] = 110
        self.assertEqual(harness.choose_rest_animation(), "sleep")


if __name__ == "__main__":
    unittest.main()
