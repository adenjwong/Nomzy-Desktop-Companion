from functools import partial

from PySide6.QtCore import QPoint, QRect, QTimer
from PySide6.QtWidgets import QApplication

from .activity import CompanionState
from .displays import (
    clamp_window_position,
    normalized_position,
    position_from_normalized,
    remap_point,
    screen_index_for_point,
)
from .macos_overlay import configure_macos_overlay_window, is_macos
from .state import load_state, save_state as write_state


class CompanionWindowMixin:
    def recalculate_window_dimensions(self):
        self.base_window_width = int(self.settings["sprite_width"]) + 30
        self.base_window_height = int(self.settings["sprite_height"]) + 30
        self.speech_window_width = int(self.settings["window_width"])
        self.speech_window_height = int(self.settings["window_height"])
        self.menu_window_width = int(self.settings["menu_window_width"])
        self.menu_window_height = int(self.settings["menu_window_height"])

    def initialize_screen_tracking(self):
        self._tracked_screens = []
        self._screen_geometries = {}
        self._display_recovery_pending = False
        self._pending_sprite_center = None
        self._pending_recovery_screen = None
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
        self._screen_geometries[id(screen)] = screen.geometry()
        screen.geometryChanged.connect(
            partial(self._handle_screen_geometry_changed, screen)
        )
        screen.availableGeometryChanged.connect(
            partial(self._handle_available_geometry_changed, screen)
        )

    def _handle_screen_added(self, screen):
        self._track_screen(screen)
        self._schedule_display_recovery()

    def _handle_screen_removed(self, screen):
        self._tracked_screens = [
            tracked for tracked in self._tracked_screens if tracked is not screen
        ]
        getattr(self, "_screen_geometries", {}).pop(id(screen), None)
        self._pending_sprite_center = None
        self._pending_recovery_screen = None
        self._schedule_display_recovery()

    def _handle_primary_screen_changed(self, screen):
        if screen is not None:
            self._track_screen(screen)
        self._schedule_display_recovery()

    # Preserve Nomzy's relative position while macOS rewrites display coordinates.
    def _handle_screen_geometry_changed(self, screen, geometry):
        previous_geometry = self._screen_geometries.get(id(screen))
        self._screen_geometries[id(screen)] = QRect(geometry)

        if previous_geometry is not None and previous_geometry != geometry:
            pending_screen = getattr(self, "_pending_recovery_screen", None)
            pending_center = getattr(self, "_pending_sprite_center", None)
            if pending_screen is screen and previous_geometry.contains(
                pending_center
            ):
                self._pending_sprite_center = remap_point(
                    pending_center,
                    previous_geometry,
                    geometry,
                )
            elif pending_center is None:
                sprite_center = self.get_sprite_global_center()
                if previous_geometry.contains(sprite_center):
                    self._pending_sprite_center = remap_point(
                        sprite_center,
                        previous_geometry,
                        geometry,
                    )
                    self._pending_recovery_screen = screen
        self._schedule_display_recovery()

    def _handle_available_geometry_changed(self, screen, geometry):
        self._schedule_display_recovery()

    def _schedule_display_recovery(self):
        if getattr(self, "_display_recovery_pending", False):
            return
        self._display_recovery_pending = True
        QTimer.singleShot(0, self._finish_display_recovery)

    def _finish_display_recovery(self):
        self._display_recovery_pending = False
        desired_center = self._pending_sprite_center
        recovery_screen = self._pending_recovery_screen
        self._pending_sprite_center = None
        self._pending_recovery_screen = None
        if desired_center is None:
            self.ensure_visible_on_available_screen()
        else:
            if recovery_screen not in QApplication.screens():
                recovery_screen = None
            self.move_sprite_center_to(desired_center, recovery_screen)

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

    @staticmethod
    def get_screen_identifier(screen):
        def screen_value(method_name):
            method = getattr(screen, method_name, None)
            return str(method()).strip() if callable(method) else ""

        serial_number = screen_value("serialNumber")
        if serial_number:
            return f"serial:{serial_number}"

        identity = "|".join(
            value
            for value in (
                screen_value("manufacturer"),
                screen_value("model"),
                screen_value("name"),
            )
            if value
        )
        return f"display:{identity}" if identity else ""

    def get_screen_by_identifier(self, screen_id):
        if not screen_id:
            return None
        return next(
            (
                screen
                for screen in QApplication.screens()
                if self.get_screen_identifier(screen) == screen_id
            ),
            None,
        )

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

    def position_for_sprite_center(self, sprite_center, screen=None):
        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)
        position = sprite_center - sprite_rect.center()
        if screen is None:
            screen = self.get_screen_for_global_point(sprite_center)
        if screen is None:
            return position
        return clamp_window_position(
            position,
            self.size(),
            screen.availableGeometry(),
        )

    def move_sprite_center_to(self, sprite_center, screen=None):
        self.move(self.position_for_sprite_center(sprite_center, screen))

    def get_centered_position(self, screen=None):
        screen = screen or QApplication.primaryScreen()
        if screen is None:
            return None
        return self.position_for_sprite_center(
            screen.availableGeometry().center(),
            screen,
        )

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
        state = {
            "sprite_center_x": sprite_center_global.x(),
            "sprite_center_y": sprite_center_global.y(),
            "last_direction": self.last_direction,
        }
        screen = self.get_screen_for_global_point(sprite_center_global)
        if screen is not None:
            screen_id = self.get_screen_identifier(screen)
            if screen_id:
                relative_x, relative_y = normalized_position(
                    sprite_center_global,
                    screen.availableGeometry(),
                )
                state.update(
                    {
                        "screen_id": screen_id,
                        "screen_relative_x": relative_x,
                        "screen_relative_y": relative_y,
                    }
                )
        write_state(state)

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
        screen = self.get_screen_by_identifier(state.get("screen_id"))
        if screen is not None:
            desired_center = position_from_normalized(
                state["screen_relative_x"],
                state["screen_relative_y"],
                screen.availableGeometry(),
            )
        return self.position_for_sprite_center(
            desired_center,
            screen,
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
