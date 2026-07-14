import random

from PySide6.QtWidgets import QApplication

from .speech import choose_speech


class CompanionBehaviorMixin:
    """Autonomous movement, speech, and reaction behavior for Nomzy."""

    def random_setting_range(self, min_key, max_key):
        min_value = int(self.settings[min_key])
        max_value = int(self.settings[max_key])

        if min_value > max_value:
            min_value, max_value = max_value, min_value

        return random.randint(min_value, max_value)

    def update_random_speech(self):
        if self.message_ticks_remaining > 0:
            self.message_ticks_remaining -= 1

            if self.message_ticks_remaining <= 0:
                self.message = ""

            return

        self.speech_cooldown_ticks -= 1

        if self.speech_cooldown_ticks <= 0:
            self.say_random_speech("idle")

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
        self.menu_visible = False
        self.message = message
        self.message_ticks_remaining = self.random_setting_range(
            "speech_min_duration_ticks",
            "speech_max_duration_ticks",
        )
        self.speech_cooldown_ticks = self.random_setting_range(
            "speech_min_ticks",
            "speech_max_ticks",
        )
        self.update_window_size_for_state()
        self.update_overlay_mask()
        self.update()
        self.enforce_always_on_top()

    def update_movement(self):
        if self.movement_state == "idle":
            self.idle_ticks_remaining -= 1

            if self.idle_ticks_remaining <= 0:
                self.start_tiny_walk()

        elif self.movement_state == "walking":
            self.walk()

    def start_tiny_walk(self):
        self.movement_state = "walking"
        self.walk_ticks_remaining = self.random_setting_range(
            "walk_min_ticks",
            "walk_max_ticks",
        )
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
        self.walk_ticks_remaining -= 1

        if self.walk_ticks_remaining <= 0:
            self.stop_walking()

    def stop_walking(self):
        self.movement_state = "idle"
        self.walk_step_x = 0
        self.walk_step_y = 0
        self.walk_ticks_remaining = 0
        self.idle_ticks_remaining = self.random_setting_range(
            "idle_min_ticks",
            "idle_max_ticks",
        )

    def pet_nomzy(self):
        self.reaction_ticks_remaining = 35
        self.movement_state = "idle"
        self.walk_ticks_remaining = 0
        self.walk_step_x = 0
        self.walk_step_y = 0
        self.idle_ticks_remaining = self.random_setting_range(
            "idle_min_ticks",
            "idle_max_ticks",
        )
