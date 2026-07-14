import math

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu

from .settings_window import NomzySettingsWindow


class CompanionInteractionMixin:
    """Radial menu actions, context menu, and mouse interaction."""

    def get_menu_buttons(self, sprite_rect):
        if not self.menu_visible:
            return []

        center = sprite_rect.center()
        radius = int(self.settings.get("menu_arc_radius", 102))
        button_radius = int(self.settings["menu_button_radius"])
        pause_label = "Resume" if self.paused else "Pause"
        items = [
            ("settings", "Settings", 210),
            ("pause", pause_label, 250),
            ("reset", "Reset", 290),
            ("quit", "Quit", 330),
            ("pet", "Pet", 30),
            ("treat", "Treat", 70),
            ("ball", "Ball", 110),
            ("talk", "Talk", 150),
        ]
        buttons = []

        for action, label, angle_degrees in items:
            angle = math.radians(angle_degrees)
            button_center_x = center.x() + int(radius * math.cos(angle))
            button_center_y = center.y() + int(radius * math.sin(angle))
            buttons.append(
                {
                    "action": action,
                    "label": label,
                    "rect": QRect(
                        button_center_x - button_radius,
                        button_center_y - button_radius,
                        button_radius * 2,
                        button_radius * 2,
                    ),
                    "group": "top" if angle_degrees > 180 else "bottom",
                }
            )
        return buttons

    def hit_menu_button(self, point):
        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)
        for button in self.get_menu_buttons(sprite_rect):
            if button["rect"].contains(point):
                return button["action"]
        return None

    def toggle_menu(self):
        self.menu_visible = not self.menu_visible
        if self.menu_visible:
            self.message = ""
            self.message_ticks_remaining = 0
            self.movement_state = "idle"
            self.walk_ticks_remaining = 0
            self.walk_step_x = 0
            self.walk_step_y = 0
        else:
            self.pending_menu_action = None
            self.close_menu_on_release = False

        self.update_window_size_for_state()
        self.update_overlay_mask()
        self.update()
        self.enforce_always_on_top()

    def close_menu(self):
        if not self.menu_visible:
            return
        self.menu_visible = False
        self.pending_menu_action = None
        self.close_menu_on_release = False
        self.update_window_size_for_state()
        self.update_overlay_mask()
        self.update()

    def execute_menu_action(self, action):
        self.close_menu()
        if action == "settings":
            self.open_settings_window()
        elif action == "pause":
            self.toggle_pause()
            self.say_random_speech("pause" if self.paused else "resume")
        elif action == "reset":
            self.reset_position()
            self.say_random_speech("reset")
        elif action == "quit":
            QApplication.quit()
        elif action in {"pet", "treat", "ball"}:
            self.pet_nomzy()
            self.say_random_speech(action)
        elif action == "talk":
            self.say_random_speech("talk")

    def open_settings_window(self):
        if self.settings_window is None:
            self.settings_window = NomzySettingsWindow(
                settings=self.settings,
                on_save=self.apply_updated_settings,
            )
        else:
            self.settings_window.load_values(self.settings)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        local_point = event.position().toPoint()
        self.pending_menu_action = None
        self.close_menu_on_release = False

        if self.menu_visible:
            self.pending_menu_action = self.hit_menu_button(local_point)
            if self.pending_menu_action is not None:
                event.accept()
                return
            if not self.point_is_on_sprite(local_point):
                self.close_menu_on_release = True
                event.accept()
                return

        self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        self.mouse_press_global = event.globalPosition().toPoint()
        self.is_dragging = False
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() != Qt.MouseButton.LeftButton:
            return
        if self.pending_menu_action is not None or self.close_menu_on_release:
            event.accept()
            return

        current_global = event.globalPosition().toPoint()
        moved_distance = (current_global - self.mouse_press_global).manhattanLength()
        if moved_distance > 4:
            self.is_dragging = True
            self.move(current_global - self.drag_position)
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.pending_menu_action is not None:
            action = self.pending_menu_action
            self.pending_menu_action = None
            self.execute_menu_action(action)
            event.accept()
            return
        if self.close_menu_on_release:
            self.close_menu()
            event.accept()
            return
        if not self.is_dragging and self.point_is_on_sprite(event.position().toPoint()):
            self.toggle_menu()
        self.is_dragging = False
        event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        actions = [
            ("Settings", self.open_settings_window),
            ("Resume Nomzy" if self.paused else "Pause Nomzy", self.toggle_pause),
            ("Say Something Now", lambda: self.say_random_speech("talk")),
            ("Reset Position", self.reset_position),
        ]
        for label, callback in actions:
            action = QAction(label, self)
            action.triggered.connect(callback)
            menu.addAction(action)
        menu.addSeparator()
        quit_action = QAction("Quit Nomzy", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        menu.exec(event.globalPos())

    def toggle_pause(self):
        self.paused = not self.paused
