from PySide6.QtCore import QElapsedTimer, QPoint, QTimer, Qt
from PySide6.QtWidgets import QWidget

from .animation import AnimationPlayer
from .behavior import CompanionBehaviorMixin
from .interactions import CompanionInteractionMixin
from .rendering import CompanionRenderingMixin
from .settings import load_settings
from .speech import load_speech
from .sprites import load_sprite_assets
from .windowing import CompanionWindowMixin


class NomzyDog(
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

        self.drag_position = QPoint()
        self.mouse_press_global = QPoint()
        self.is_dragging = False
        self.pending_menu_action = None
        self.close_menu_on_release = False
        self.menu_visible = False

        self.paused = False
        self.movement_state = "idle"
        self.idle_ticks_remaining = self.random_setting_range(
            "idle_min_ticks",
            "idle_max_ticks",
        )
        self.walk_ticks_remaining = 0
        self.walk_step_x = 0
        self.walk_step_y = 0
        self.last_direction = 1

        self.message = ""
        self.message_ticks_remaining = 0
        self.speech_cooldown_ticks = self.random_setting_range(
            "speech_min_ticks",
            "speech_max_ticks",
        )
        sprite_assets = load_sprite_assets()
        self.sprite_frames = sprite_assets.frames
        self.sprite_anchor_x = sprite_assets.anchor_x
        self.sprite_anchor_y = sprite_assets.anchor_y
        self.animation_player = AnimationPlayer(sprite_assets.clips, "idle")
        self.active_reaction = None
        self.ambient_animation = None
        self.talk_animation_pending = False
        self.blink_cooldown_ms = self.random_blink_cooldown()
        self.reaction_ticks_remaining = 0

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

        if not self.paused and not self.menu_visible:
            if self.settings["movement_enabled"]:
                self.update_movement()
            if self.settings["speech_enabled"]:
                self.update_random_speech()

        self.update_animation(elapsed_ms)

        self.update_window_size_for_state()
        self.update_overlay_mask()
        self.update()
