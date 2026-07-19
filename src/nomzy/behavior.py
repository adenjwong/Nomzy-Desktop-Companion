import random

from PySide6.QtWidgets import QApplication

from .activity import CompanionEvent
from .scheduling import BehaviorAction
from .speech import choose_speech


class CompanionBehaviorMixin:
    """Autonomous movement, speech, and reaction behavior for Nomzy."""

    def perform_scheduled_action(self, action: BehaviorAction | None):
        if action is None:
            return
        if action is BehaviorAction.START_WALKING:
            self.start_tiny_walk()
        elif action is BehaviorAction.WALK_STEP:
            self.walk()
        elif action is BehaviorAction.SPEAK:
            self.say_random_speech("idle")
        elif action is BehaviorAction.HIDE_MESSAGE:
            self.hide_message()
        elif action is BehaviorAction.REST:
            self.start_resting()
        elif action is BehaviorAction.BLINK:
            self.transition_activity(CompanionEvent.START_BLINKING)

    def hide_message(self):
        self.message = ""
        self.scheduler.clear_message()
        self.transition_activity(CompanionEvent.STOP_TALKING)

    def say_random_speech(self, category="idle"):
        message = choose_speech(self.speech, category)
        self.say_message(self.personalize_speech(message))

    def personalize_speech(self, message: str) -> str:
        return message.replace("{name}", self.get_household_name())

    def get_household_name(self) -> str:
        user_name = str(self.settings.get("user_name", "")).strip()
        little_names = {"aden": "dad", "ethney": "mom"}

        if user_name.casefold() in little_names:
            return little_names[user_name.casefold()]

        return user_name or "friend"

    def say_message(self, message):
        self.transition_activity(CompanionEvent.CLOSE_MENU)
        self.message = message
        self.transition_activity(CompanionEvent.START_TALKING)
        self.scheduler.start_message()
        self.update_animation(0)
        self.update_window_size_for_state()
        self.update_overlay_mask()
        self.update()
        self.enforce_always_on_top()

    def start_tiny_walk(self):
        transition = self.transition_activity(CompanionEvent.START_WALKING)
        if not transition.changed:
            return

        if self.scheduler.walk_ticks_remaining <= 0:
            self.scheduler.start_walk()
        possible_steps = [-1, 0, 1]
        self.walk_step_x = random.choice(possible_steps)
        self.walk_step_y = random.choice(possible_steps)

        while self.walk_step_x == 0 and self.walk_step_y == 0:
            self.walk_step_x = random.choice(possible_steps)
            self.walk_step_y = random.choice(possible_steps)

        if self.walk_step_x != 0:
            self.last_direction = 1 if self.walk_step_x > 0 else -1

    def walk(self):
        new_x = self.x() + self.walk_step_x
        new_y = self.y() + self.walk_step_y
        screen = self.screen() or QApplication.primaryScreen()
        bounds = screen.availableGeometry()
        left = bounds.left()
        right = bounds.right() - self.width()
        top = bounds.top()
        bottom = bounds.bottom() - self.height()

        if new_x <= left or new_x >= right:
            self.walk_step_x *= -1
            new_x = max(left, min(new_x, right))

            if self.walk_step_x != 0:
                self.last_direction = 1 if self.walk_step_x > 0 else -1

        if new_y <= top or new_y >= bottom:
            self.walk_step_y *= -1
            new_y = max(top, min(new_y, bottom))

        self.move(int(new_x), int(new_y))
        if self.scheduler.complete_walk_step():
            self.stop_walking()

    def stop_walking(self):
        self.transition_activity(CompanionEvent.STOP_WALKING)

    def pet_nomzy(self, animation_name="pet"):
        self.start_reaction(animation_name)

    def choose_rest_animation(self):
        sleep_chance = int(self.settings.get("sleep_chance_percent", 30))
        sleep_chance = max(0, min(sleep_chance, 100))
        return "sleep" if random.randint(1, 100) <= sleep_chance else "sit"

    def start_resting(self):
        rest_animation = self.choose_rest_animation()
        rest_event = {
            "sit": CompanionEvent.START_SITTING,
            "sleep": CompanionEvent.START_SLEEPING,
        }[rest_animation]
        self.transition_activity(rest_event)

    def start_reaction(self, animation_name):
        if animation_name not in self.animation_player.clips:
            animation_name = "pet"

        self.transition_activity(
            CompanionEvent.START_REACTION,
            animation_name=animation_name,
        )

    def resolve_finished_animation(self):
        player = self.animation_player
        if player.finished and player.clip.returns_to_activity:
            self.transition_activity(
                CompanionEvent.ANIMATION_FINISHED,
                animation_name=player.clip_name,
            )

    def update_animation(self, elapsed_ms):
        player = self.animation_player
        desired_animation = self.activity.animation_name
        player.play(
            desired_animation,
            restart=self.activity.consume_animation_restart(),
        )
        player.advance(elapsed_ms)
