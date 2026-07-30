from PySide6.QtCore import QPoint, QTimer
from PySide6.QtWidgets import QApplication

from .activity import CompanionState
from .displays import clamp_window_position, screen_index_for_point
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

    def initialize_screen_tracking(self):
        self._tracked_screens = []
        application = QApplication.instance()
        if application is None:
            return

        application.screenAdded.connect(self._handle_screen_added)
        application.screenRemoved.connect(self._handle_screen_removed)
        application.primaryScreenChanged.connect(
            self._handle_primary_screen_changed
        )
        for screen in application.screens():
            self._track_screen(screen)

    def _track_screen(self, screen):
        if any(tracked is screen for tracked in self._tracked_screens):
            return
        self._tracked_screens.append(screen)
        screen.availableGeometryChanged.connect(
            self._handle_screen_geometry_changed
        )

    def _handle_screen_added(self, screen):
        self._track_screen(screen)

    def _handle_screen_removed(self, screen):
        self._tracked_screens = [
            tracked for tracked in self._tracked_screens if tracked is not screen
        ]
        QTimer.singleShot(0, self.ensure_visible_on_available_screen)

    def _handle_primary_screen_changed(self, screen):
        if screen is not None:
            self._track_screen(screen)
        QTimer.singleShot(0, self.ensure_visible_on_available_screen)

    def _handle_screen_geometry_changed(self, geometry):
        self.ensure_visible_on_available_screen()

    def get_screen_for_global_point(self, point):
        screens = QApplication.screens()
        if not screens:
            return QApplication.primaryScreen()

        geometries = [screen.availableGeometry() for screen in screens]
        screen_index = screen_index_for_point(geometries, point)
        if screen_index is None:
            return QApplication.primaryScreen()
        return screens[screen_index]

    def get_sprite_global_center(self):
        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)
        return self.mapToGlobal(sprite_rect.center())

    def get_current_screen(self):
        return self.get_screen_for_global_point(self.get_sprite_global_center())

    def clamp_position_to_available_screen(
        self,
        x,
        y,
        reference_point=None,
    ):
        position = QPoint(int(x), int(y))
        if reference_point is None:
            reference_point = position + QPoint(
                self.width() // 2,
                self.height() // 2,
            )

        screen = self.get_screen_for_global_point(reference_point)
        if screen is None:
            return position
        return clamp_window_position(
            position,
            self.size(),
            screen.availableGeometry(),
        )

    def ensure_visible_on_available_screen(self):
        sprite_center = self.get_sprite_global_center()
        position = self.clamp_position_to_available_screen(
            self.x(),
            self.y(),
            reference_point=sprite_center,
        )
        if position != self.pos():
            self.move(position)

    def showEvent(self, event):
        super().showEvent(event)
        self.ensure_visible_on_available_screen()
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

        self.last_direction = state["last_direction"]
        desired_center = QPoint(
            state["sprite_center_x"],
            state["sprite_center_y"],
        )
        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(
            scaled_sprite,
            force_message=False,
            force_menu=False,
        )
        top_left = desired_center - sprite_rect.center()
        return self.clamp_position_to_available_screen(
            top_left.x(),
            top_left.y(),
            reference_point=desired_center,
        )

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
        if self.activity.menu_open:
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
        desired_position = old_sprite_center_global - new_sprite_rect.center()
        self.move(
            self.clamp_position_to_available_screen(
                desired_position.x(),
                desired_position.y(),
                reference_point=old_sprite_center_global,
            )
        )
        self.update_overlay_mask()
        self.enforce_always_on_top()

    def apply_updated_settings(self, updated_settings: dict):
        old_scaled_sprite = self.get_scaled_sprite()
        old_sprite_rect = self.get_sprite_rect(old_scaled_sprite)
        old_sprite_center_global = self.mapToGlobal(old_sprite_rect.center())
        self.settings = dict(updated_settings)
        self.scheduler.update_settings(self.settings)
        self.recalculate_window_dimensions()
        if self.activity.state is CompanionState.IDLE:
            self.scheduler.reset_walk()

        if self.activity.menu_open:
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
        desired_position = old_sprite_center_global - new_sprite_rect.center()
        self.move(
            self.clamp_position_to_available_screen(
                desired_position.x(),
                desired_position.y(),
                reference_point=old_sprite_center_global,
            )
        )
        self.update_overlay_mask()
        self.update()
        self.enforce_always_on_top()

    def reset_position(self):
        screen = self.get_current_screen() or QApplication.primaryScreen()
        if screen is None:
            return
        bounds = screen.availableGeometry()
        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)
        new_top_left = bounds.center() - sprite_rect.center()
        self.move(
            self.clamp_position_to_available_screen(
                new_top_left.x(),
                new_top_left.y(),
                reference_point=bounds.center(),
            )
        )
        self.update_overlay_mask()
        self.enforce_always_on_top()
