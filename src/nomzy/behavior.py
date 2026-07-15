import random

from PySide6.QtWidgets import QApplication

from .speech import choose_speech


TICKS_PER_SECOND = 25


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
        self.talk_animation_pending = True
        self.message_ticks_remaining = self.random_setting_range(
            "speech_min_duration_ticks",
            "speech_max_duration_ticks",
        )
        self.speech_cooldown_ticks = self.random_setting_range(
            "speech_min_ticks",
            "speech_max_ticks",
        )
        self.update_animation(0)
        self.update_window_size_for_state()
        self.update_overlay_mask()
        self.update()
        self.enforce_always_on_top()

    def update_movement(self):
        if self.is_dragging:
            return

        if self.movement_state == "idle":
            if self.ambient_animation in {"sit", "sleep"}:
                return

            self.idle_ticks_remaining -= 1

            if self.idle_ticks_remaining <= 0:
                self.start_tiny_walk()

        elif self.movement_state == "walking":
            self.walk()

    def random_walk_cooldown_ticks(self):
        interval_seconds = max(
            1,
            int(self.settings.get("walk_interval_seconds", 10)),
        )
        interval_ticks = interval_seconds * TICKS_PER_SECOND
        variation = max(1, round(interval_ticks * 0.25))
        return random.randint(
            max(1, interval_ticks - variation),
            interval_ticks + variation,
        )

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
        self.idle_ticks_remaining = self.random_walk_cooldown_ticks()

    def pet_nomzy(self, animation_name="pet"):
        self.movement_state = "idle"
        self.walk_ticks_remaining = 0
        self.walk_step_x = 0
        self.walk_step_y = 0
        self.idle_ticks_remaining = self.random_walk_cooldown_ticks()
        self.start_reaction(animation_name)

    def random_blink_cooldown(self):
        min_interval = int(self.settings.get("blink_min_interval_ms", 6000))
        max_interval = int(self.settings.get("blink_max_interval_ms", 12000))

        if min_interval > max_interval:
            min_interval, max_interval = max_interval, min_interval

        return random.randint(max(1, min_interval), max(1, max_interval))

    def random_rest_cooldown(self):
        min_interval = int(self.settings.get("rest_min_interval_ms", 45000))
        max_interval = int(self.settings.get("rest_max_interval_ms", 120000))

        if min_interval > max_interval:
            min_interval, max_interval = max_interval, min_interval

        return random.randint(max(1, min_interval), max(1, max_interval))

    def choose_rest_animation(self):
        sleep_chance = int(self.settings.get("sleep_chance_percent", 30))
        sleep_chance = max(0, min(sleep_chance, 100))
        return "sleep" if random.randint(1, 100) <= sleep_chance else "sit"

    def start_reaction(self, animation_name):
        if animation_name not in self.animation_player.clips:
            animation_name = "pet"

        self.active_reaction = animation_name
        self.ambient_animation = None
        self.animation_player.play(animation_name, restart=True)

    def update_animation(self, elapsed_ms):
        player = self.animation_player

        if player.finished:
            if self.active_reaction == player.clip_name:
                self.active_reaction = None
            if self.ambient_animation == player.clip_name:
                self.ambient_animation = None

        idle_can_animate = (
            not self.is_dragging
            and not self.paused
            and not self.menu_visible
            and not self.message
            and self.movement_state == "idle"
            and self.active_reaction is None
        )

        if idle_can_animate:
            self.blink_cooldown_ms -= elapsed_ms
            self.rest_cooldown_ms -= elapsed_ms

            if self.ambient_animation is None:
                if self.rest_cooldown_ms <= 0:
                    self.ambient_animation = self.choose_rest_animation()
                    self.rest_cooldown_ms = self.random_rest_cooldown()
                elif self.blink_cooldown_ms <= 0:
                    self.ambient_animation = "blink"
                    self.blink_cooldown_ms = self.random_blink_cooldown()
        else:
            self.ambient_animation = None

        if self.is_dragging:
            desired_animation = "drag"
        elif self.paused or self.menu_visible:
            desired_animation = "paused"
        elif self.active_reaction is not None:
            desired_animation = self.active_reaction
        elif self.message:
            desired_animation = "talk"
        elif self.movement_state == "walking":
            desired_animation = "walk"
        elif self.ambient_animation is not None:
            desired_animation = self.ambient_animation
        else:
            desired_animation = "idle"

        restart_talk = (
            desired_animation == "talk" and self.talk_animation_pending
        )
        restart_drag = (
            desired_animation == "drag" and self.drag_animation_pending
        )
        player.play(
            desired_animation,
            restart=restart_talk or restart_drag,
        )

        if desired_animation == "talk":
            self.talk_animation_pending = False
        if desired_animation == "drag":
            self.drag_animation_pending = False

        player.advance(elapsed_ms)
