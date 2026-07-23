from PySide6.QtCore import QElapsedTimer, QPoint, QTimer, Qt
from PySide6.QtWidgets import QWidget

from .activity import CompanionActivityMixin, CompanionStateMachine
from .animation import AnimationPlayer
from .behavior import CompanionBehaviorMixin
from .interactions import CompanionInteractionMixin
from .rendering import CompanionRenderingMixin
from .scheduling import BehaviorScheduler
from .settings import load_settings
from .speech import load_speech
from .sprites import load_sprite_assets
from .windowing import CompanionWindowMixin


class NomzyDog(
    CompanionActivityMixin,
    CompanionWindowMixin,
    CompanionBehaviorMixin,
    CompanionInteractionMixin,
    CompanionRenderingMixin,
    QWidget,
):
    """The Nomzy desktop companion widget.

    Feature-specific behavior lives in focused mixins while this class owns the
    companion's state, initialization, timers, and main update loop.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nomzy Desktop Companion")

        self.settings = load_settings()
        self.speech = load_speech()
        self.settings_window = None
        sprite_assets = load_sprite_assets()
        self.activity = CompanionStateMachine(sprite_assets.activity_clips)
        self.scheduler = BehaviorScheduler(self.settings)

        self.recalculate_window_dimensions()
        self.setFixedSize(self.base_window_width, self.base_window_height)

        window_flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.BypassWindowManagerHint
        )
        if self.settings.get("always_on_top", True):
            window_flags |= Qt.WindowType.WindowStaysOnTopHint
        if self.settings.get("prevent_focus_steal", True):
            window_flags |= Qt.WindowType.WindowDoesNotAcceptFocus
        self.setWindowFlags(window_flags)

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAutoFillBackground(False)

        self.mouse_press_global = QPoint()
        self.drag_direction_x = 0
        self.pending_menu_action = None
        self.close_menu_on_release = False

        self.walk_step_x = 0
        self.walk_step_y = 0
        self.last_direction = 1

        self.message = ""
        self.sprite_frames = sprite_assets.frames
        self.sprite_anchor_x = sprite_assets.anchor_x
        self.sprite_anchor_y = sprite_assets.anchor_y
        self.animation_player = AnimationPlayer(sprite_assets.clips, "idle")

        self.animation_clock = QElapsedTimer()
        self.animation_clock.start()

        self.timer = self._start_timer(40, self.tick)
        self.topmost_timer = self._start_timer(1000, self.enforce_always_on_top)
        self.position_save_timer = self._start_timer(5000, self.save_state)
        self.mask_timer = self._start_timer(120, self.update_overlay_mask)
        self.native_overlay_timer = self._start_timer(
            1500,
            self.apply_native_overlay_style,
        )

    def _start_timer(self, interval_ms, callback):
        timer = QTimer(self)
        timer.timeout.connect(callback)
        timer.start(interval_ms)
        return timer

    def tick(self):
        elapsed_ms = max(0, min(self.animation_clock.restart(), 250))
        background_updates_enabled = not self.activity.blocks_background_updates

        if background_updates_enabled:
            movement_action = self.scheduler.next_movement_action(
                self.activity.state,
                enabled=bool(self.settings["movement_enabled"]),
            )
            self.perform_scheduled_action(movement_action)

        speech_action = self.scheduler.next_speech_action(
            enabled=(
                background_updates_enabled
                and bool(self.settings["speech_enabled"])
            ),
        )
        self.perform_scheduled_action(speech_action)

        self.resolve_finished_animation()
        ambient_action = self.scheduler.next_ambient_action(
            self.activity.state,
            elapsed_ms,
        )
        self.perform_scheduled_action(ambient_action)
        self.update_animation(elapsed_ms)

        self.update_window_size_for_state()
        self.update_overlay_mask()
        self.update()
