import unittest

from nomzy.activity import CompanionEvent, CompanionState, CompanionStateMachine


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


class CompanionStateMachineTests(unittest.TestCase):
    def setUp(self):
        self.activity = CompanionStateMachine(ACTIVITY_CLIPS)

    def test_walk_starts_and_stops_from_idle(self):
        self.activity.dispatch(CompanionEvent.START_WALKING)
        self.assertEqual(self.activity.state, CompanionState.WALKING)

        self.activity.dispatch(CompanionEvent.STOP_WALKING)
        self.assertEqual(self.activity.state, CompanionState.IDLE)

    def test_reaction_finishes_before_talking_animation_begins(self):
        self.activity.dispatch(CompanionEvent.START_REACTION, "treat")
        self.activity.dispatch(CompanionEvent.START_TALKING)

        self.assertEqual(self.activity.state, CompanionState.REACTING)
        self.assertEqual(self.activity.animation_name, "treat")

        self.activity.dispatch(CompanionEvent.ANIMATION_FINISHED, "treat")
        self.assertEqual(self.activity.state, CompanionState.TALKING)

    def test_dragging_interrupts_rest_and_returns_to_talking(self):
        self.activity.dispatch(CompanionEvent.START_SLEEPING)
        self.activity.dispatch(CompanionEvent.START_TALKING)
        self.activity.dispatch(CompanionEvent.START_DRAGGING)

        self.assertEqual(self.activity.state, CompanionState.DRAGGING)

        self.activity.dispatch(CompanionEvent.STOP_DRAGGING)
        self.assertEqual(self.activity.state, CompanionState.TALKING)

    def test_drag_release_respects_pause(self):
        self.activity.dispatch(CompanionEvent.PAUSE)
        self.activity.dispatch(CompanionEvent.START_DRAGGING)
        self.activity.dispatch(CompanionEvent.STOP_DRAGGING)

        self.assertEqual(self.activity.state, CompanionState.PAUSED)

    def test_menu_closes_back_to_paused_state(self):
        self.activity.dispatch(CompanionEvent.PAUSE)
        self.activity.dispatch(CompanionEvent.OPEN_MENU)
        self.assertEqual(self.activity.state, CompanionState.MENU)

        self.activity.dispatch(CompanionEvent.CLOSE_MENU)
        self.assertEqual(self.activity.state, CompanionState.PAUSED)

    def test_reaction_resumes_after_pause(self):
        self.activity.dispatch(CompanionEvent.START_REACTION, "ball")
        self.activity.dispatch(CompanionEvent.PAUSE)
        self.assertEqual(self.activity.state, CompanionState.PAUSED)

        self.activity.dispatch(CompanionEvent.RESUME)
        self.assertEqual(self.activity.state, CompanionState.REACTING)
        self.assertEqual(self.activity.animation_name, "ball")

    def test_opening_menu_cancels_active_speech(self):
        self.activity.dispatch(CompanionEvent.START_TALKING)
        self.activity.dispatch(CompanionEvent.OPEN_MENU)
        self.activity.dispatch(CompanionEvent.CLOSE_MENU)

        self.assertFalse(self.activity.message_active)
        self.assertEqual(self.activity.state, CompanionState.IDLE)

    def test_ambient_animation_returns_to_idle_when_finished(self):
        self.activity.dispatch(CompanionEvent.START_BLINKING)
        self.activity.dispatch(CompanionEvent.ANIMATION_FINISHED, "blink")

        self.assertEqual(self.activity.state, CompanionState.IDLE)

    def test_state_change_requests_one_animation_restart(self):
        self.activity.dispatch(CompanionEvent.START_DRAGGING)

        self.assertTrue(self.activity.consume_animation_restart())
        self.assertFalse(self.activity.consume_animation_restart())


if __name__ == "__main__":
    unittest.main()
