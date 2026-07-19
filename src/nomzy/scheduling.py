import random
from enum import Enum, auto

from .activity import CompanionState


TICKS_PER_SECOND = 25


class BehaviorAction(Enum):
    START_WALKING = auto()
    WALK_STEP = auto()
    SPEAK = auto()
    HIDE_MESSAGE = auto()
    REST = auto()
    BLINK = auto()


class BehaviorScheduler:
    """Owns Nomzy's independent behavior countdowns and emits due actions."""

    def __init__(self, settings: dict, rng=None):
        self.settings = dict(settings)
        self.rng = rng if rng is not None else random
        self.walk_ticks_remaining = 0
        self.message_ticks_remaining = 0
        self.reset_walk()
        self.speech_cooldown_ticks = self._setting_range(
            "speech_min_ticks",
            "speech_max_ticks",
            1500,
            4500,
        )
        self.blink_cooldown_ms = self._random_interval(
            "blink_min_interval_ms",
            "blink_max_interval_ms",
            6000,
            12000,
        )
        self.rest_cooldown_ms = self._random_interval(
            "rest_min_interval_ms",
            "rest_max_interval_ms",
            45000,
            120000,
        )

    def update_settings(self, settings: dict) -> None:
        self.settings = dict(settings)
        speech_max = int(self.settings.get("speech_max_ticks", 4500))
        self.speech_cooldown_ticks = min(
            self.speech_cooldown_ticks,
            speech_max,
        )

    def next_movement_action(
        self,
        state: CompanionState,
        enabled: bool,
    ) -> BehaviorAction | None:
        if not enabled:
            return None

        if state is CompanionState.IDLE:
            self.walk_cooldown_ticks -= 1
            if self.walk_cooldown_ticks <= 0:
                self.start_walk()
                return BehaviorAction.START_WALKING
        elif state is CompanionState.WALKING:
            return BehaviorAction.WALK_STEP

        return None

    def start_walk(self) -> None:
        self.walk_ticks_remaining = self._setting_range(
            "walk_min_ticks",
            "walk_max_ticks",
            10,
            35,
        )

    def complete_walk_step(self) -> bool:
        self.walk_ticks_remaining -= 1
        return self.walk_ticks_remaining <= 0

    def reset_walk(self) -> None:
        self.walk_ticks_remaining = 0
        interval_seconds = max(
            1,
            int(self.settings.get("walk_interval_seconds", 10)),
        )
        interval_ticks = interval_seconds * TICKS_PER_SECOND
        variation = max(1, round(interval_ticks * 0.25))
        self.walk_cooldown_ticks = self.rng.randint(
            max(1, interval_ticks - variation),
            interval_ticks + variation,
        )

    def next_speech_action(self, enabled: bool) -> BehaviorAction | None:
        if not enabled:
            return None

        if self.message_ticks_remaining > 0:
            self.message_ticks_remaining -= 1
            if self.message_ticks_remaining <= 0:
                return BehaviorAction.HIDE_MESSAGE
            return None

        self.speech_cooldown_ticks -= 1
        if self.speech_cooldown_ticks <= 0:
            return BehaviorAction.SPEAK
        return None

    def start_message(self) -> None:
        self.message_ticks_remaining = self._setting_range(
            "speech_min_duration_ticks",
            "speech_max_duration_ticks",
            75,
            125,
        )
        self.speech_cooldown_ticks = self._setting_range(
            "speech_min_ticks",
            "speech_max_ticks",
            1500,
            4500,
        )

    def clear_message(self) -> None:
        self.message_ticks_remaining = 0

    def next_ambient_action(
        self,
        state: CompanionState,
        elapsed_ms: int,
    ) -> BehaviorAction | None:
        elapsed_ms = max(0, int(elapsed_ms))

        if state in {CompanionState.IDLE, CompanionState.BLINKING}:
            self.rest_cooldown_ms -= elapsed_ms

        if state is not CompanionState.IDLE:
            return None

        self.blink_cooldown_ms -= elapsed_ms
        if self.rest_cooldown_ms <= 0:
            self.rest_cooldown_ms = self._random_interval(
                "rest_min_interval_ms",
                "rest_max_interval_ms",
                45000,
                120000,
            )
            return BehaviorAction.REST
        if self.blink_cooldown_ms <= 0:
            self.blink_cooldown_ms = self._random_interval(
                "blink_min_interval_ms",
                "blink_max_interval_ms",
                6000,
                12000,
            )
            return BehaviorAction.BLINK

        return None

    def _setting_range(
        self,
        min_key: str,
        max_key: str,
        default_min: int,
        default_max: int,
    ) -> int:
        min_value = int(self.settings.get(min_key, default_min))
        max_value = int(self.settings.get(max_key, default_max))
        if min_value > max_value:
            min_value, max_value = max_value, min_value
        return self.rng.randint(min_value, max_value)

    def _random_interval(
        self,
        min_key: str,
        max_key: str,
        default_min: int,
        default_max: int,
    ) -> int:
        min_value = max(1, int(self.settings.get(min_key, default_min)))
        max_value = max(1, int(self.settings.get(max_key, default_max)))
        if min_value > max_value:
            min_value, max_value = max_value, min_value
        return self.rng.randint(min_value, max_value)
