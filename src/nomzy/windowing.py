from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from .macos_overlay import configure_macos_overlay_window, is_macos
from .state import load_state, save_state as write_state


class CompanionWindowMixin:
    """Window sizing, placement, persistence, and native overlay behavior."""

    def recalculate_window_dimensions(self):
        self.base_window_width = int(self.settings["sprite_width"]) + 30
        self.base_window_height = int(self.settings["sprite_height"]) + 30
        self.speech_window_width = int(self.settings["window_width"])
        self.speech_window_height = int(self.settings["window_height"])
        self.menu_window_width = int(self.settings["menu_window_width"])
        self.menu_window_height = int(self.settings["menu_window_height"])

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_native_overlay_style()
        self.update_overlay_mask()
        self.enforce_always_on_top()

    def apply_native_overlay_style(self):
        if not self.settings.get("native_macos_overlay_enabled", True):
            return
        if not is_macos():
            return

        configure_macos_overlay_window(
            self,
            window_level=str(self.settings.get("macos_window_level", "status")),
            prevent_activation=bool(self.settings.get("prevent_focus_steal", True)),
        )

    def save_state(self):
        if not self.settings.get("save_position", True):
            return

        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)
        sprite_center_global = self.mapToGlobal(sprite_rect.center())
        write_state(
            {
                "sprite_center_x": sprite_center_global.x(),
                "sprite_center_y": sprite_center_global.y(),
                "last_direction": self.last_direction,
            }
        )

    def get_saved_position(self):
        if not self.settings.get("save_position", True):
            return None

        state = load_state()
        if "sprite_center_x" not in state or "sprite_center_y" not in state:
            return None

        self.last_direction = int(state.get("last_direction", 1))
        desired_center = QPoint(
            int(state["sprite_center_x"]),
            int(state["sprite_center_y"]),
        )
        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(
            scaled_sprite,
            force_message=False,
            force_menu=False,
        )
        top_left = desired_center - sprite_rect.center()
        return self.clamp_position_to_screen(top_left.x(), top_left.y())

    def clamp_position_to_screen(self, x, y):
        bounds = QApplication.primaryScreen().availableGeometry()
        clamped_x = max(bounds.left(), min(x, bounds.right() - self.width()))
        clamped_y = max(bounds.top(), min(y, bounds.bottom() - self.height()))
        return QPoint(clamped_x, clamped_y)

    def closeEvent(self, event):
        self.save_state()
        event.accept()

    def enforce_always_on_top(self):
        if not self.settings.get("always_on_top", True):
            return
        if is_macos():
            self.apply_native_overlay_style()
        else:
            self.raise_()

    def update_window_size_for_state(self):
        if self.menu_visible:
            desired_width = self.menu_window_width
            desired_height = self.menu_window_height
            desired_message, desired_menu = False, True
        elif self.message:
            desired_width = self.speech_window_width
            desired_height = self.speech_window_height
            desired_message, desired_menu = True, False
        else:
            desired_width = self.base_window_width
            desired_height = self.base_window_height
            desired_message, desired_menu = False, False

        if self.width() == desired_width and self.height() == desired_height:
            return

        current_menu_layout = (
            self.width() == self.menu_window_width
            and self.height() == self.menu_window_height
        )
        current_speech_layout = (
            self.width() == self.speech_window_width
            and self.height() == self.speech_window_height
        )
        scaled_sprite = self.get_scaled_sprite()
        old_sprite_rect = self.get_sprite_rect(
            scaled_sprite,
            force_message=current_speech_layout,
            force_menu=current_menu_layout,
        )
        old_sprite_center_global = self.mapToGlobal(old_sprite_rect.center())

        self.clearMask()
        self.setFixedSize(desired_width, desired_height)
        new_sprite_rect = self.get_sprite_rect(
            scaled_sprite,
            force_message=desired_message,
            force_menu=desired_menu,
        )
        self.move(old_sprite_center_global - new_sprite_rect.center())
        self.update_overlay_mask()
        self.enforce_always_on_top()

    def apply_updated_settings(self, updated_settings: dict):
        old_scaled_sprite = self.get_scaled_sprite()
        old_sprite_rect = self.get_sprite_rect(old_scaled_sprite)
        old_sprite_center_global = self.mapToGlobal(old_sprite_rect.center())
        self.settings = dict(updated_settings)
        self.recalculate_window_dimensions()
        self.speech_cooldown_ticks = min(
            self.speech_cooldown_ticks,
            int(self.settings["speech_max_ticks"]),
        )

        if self.menu_visible:
            desired_width, desired_height = (
                self.menu_window_width,
                self.menu_window_height,
            )
        elif self.message:
            desired_width, desired_height = (
                self.speech_window_width,
                self.speech_window_height,
            )
        else:
            desired_width, desired_height = (
                self.base_window_width,
                self.base_window_height,
            )

        self.clearMask()
        self.setFixedSize(desired_width, desired_height)
        new_scaled_sprite = self.get_scaled_sprite()
        new_sprite_rect = self.get_sprite_rect(new_scaled_sprite)
        self.move(old_sprite_center_global - new_sprite_rect.center())
        self.update_overlay_mask()
        self.update()
        self.enforce_always_on_top()

    def reset_position(self):
        bounds = QApplication.primaryScreen().availableGeometry()
        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)
        new_top_left = bounds.center() - sprite_rect.center()
        self.move(new_top_left)
        self.update_overlay_mask()
        self.enforce_always_on_top()
