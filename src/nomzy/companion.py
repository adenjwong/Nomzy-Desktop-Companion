import math
import random
import sys

from PySide6.QtCore import QPoint, QRect, QSize, QTimer, Qt
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QPainter,
    QPen,
    QPixmap,
    QPolygon,
    QRegion,
)
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from .macos_overlay import configure_macos_overlay_window, is_macos
from .settings import load_settings
from .speech import choose_speech, load_speech
from .sprites import load_sprite_frames
from .state import load_state, save_state as write_state


class NomzyDog(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Nomzy Desktop Companion")

        self.settings = load_settings()
        self.speech = load_speech()

        self.base_window_width = int(self.settings["sprite_width"]) + 30
        self.base_window_height = int(self.settings["sprite_height"]) + 30

        self.speech_window_width = int(self.settings["window_width"])
        self.speech_window_height = int(self.settings["window_height"])

        self.menu_window_width = int(self.settings["menu_window_width"])
        self.menu_window_height = int(self.settings["menu_window_height"])

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

        self.frame = 0
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

        self.reaction_ticks_remaining = 0
        self.sprite_frames = load_sprite_frames()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(40)

        self.topmost_timer = QTimer(self)
        self.topmost_timer.timeout.connect(self.enforce_always_on_top)
        self.topmost_timer.start(1000)

        self.position_save_timer = QTimer(self)
        self.position_save_timer.timeout.connect(self.save_state)
        self.position_save_timer.start(5000)

        self.mask_timer = QTimer(self)
        self.mask_timer.timeout.connect(self.update_overlay_mask)
        self.mask_timer.start(120)

        self.native_overlay_timer = QTimer(self)
        self.native_overlay_timer.timeout.connect(self.apply_native_overlay_style)
        self.native_overlay_timer.start(1500)

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
            window_level=str(self.settings.get("macos_window_level", "floating")),
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

        write_state(state)

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
        screen = QApplication.primaryScreen()
        bounds = screen.availableGeometry()

        clamped_x = max(
            bounds.left(),
            min(x, bounds.right() - self.width()),
        )

        clamped_y = max(
            bounds.top(),
            min(y, bounds.bottom() - self.height()),
        )

        return QPoint(clamped_x, clamped_y)

    def closeEvent(self, event):
        self.save_state()
        event.accept()

    def random_setting_range(self, min_key, max_key):
        min_value = int(self.settings[min_key])
        max_value = int(self.settings[max_key])

        if min_value > max_value:
            min_value, max_value = max_value, min_value

        return random.randint(min_value, max_value)

    def tick(self):
        self.frame += 1

        if not self.paused and not self.menu_visible:
            if self.settings["movement_enabled"]:
                self.update_movement()

            if self.settings["speech_enabled"]:
                self.update_random_speech()

        if self.reaction_ticks_remaining > 0:
            self.reaction_ticks_remaining -= 1

        self.update_window_size_for_state()
        self.update_overlay_mask()
        self.update()

    def enforce_always_on_top(self):
        if not self.settings.get("always_on_top", True):
            return

        if is_macos():
            self.apply_native_overlay_style()
            return

        self.raise_()

    def update_overlay_mask(self):
        if not self.settings.get("overlay_mode_enabled", True):
            self.clearMask()
            return

        if not self.settings.get("overlay_mask_enabled", True):
            self.clearMask()
            return

        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)

        padding = int(self.settings.get("sprite_click_padding", 8))

        region = QRegion(
            sprite_rect.adjusted(
                -padding,
                -padding,
                padding,
                padding,
            )
        )

        if self.menu_visible:
            for button in self.get_menu_buttons(sprite_rect):
                button_region = QRegion(
                    button["rect"],
                    QRegion.RegionType.Ellipse,
                )
                region = region.united(button_region)

        if self.message and self.settings.get("speech_bubble_blocks_input", True):
            bubble_rect, tail = self.get_speech_bubble_geometry(sprite_rect)

            if bubble_rect is not None:
                bubble_region = QRegion(
                    bubble_rect.adjusted(-3, -3, 3, 3),
                    QRegion.RegionType.Rectangle,
                )
                region = region.united(bubble_region)

            if tail is not None:
                tail_region = QRegion(tail)
                region = region.united(tail_region)

        self.setMask(region)

    def update_window_size_for_state(self):
        if self.menu_visible:
            desired_width = self.menu_window_width
            desired_height = self.menu_window_height
            desired_message = False
            desired_menu = True
        elif self.message:
            desired_width = self.speech_window_width
            desired_height = self.speech_window_height
            desired_message = True
            desired_menu = False
        else:
            desired_width = self.base_window_width
            desired_height = self.base_window_height
            desired_message = False
            desired_menu = False

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
        new_top_left = old_sprite_center_global - new_sprite_rect.center()

        self.move(new_top_left)
        self.update_overlay_mask()
        self.apply_native_overlay_style()
        self.enforce_always_on_top()

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
        self.say_message(message)

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

            return

        if self.movement_state == "walking":
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

    def current_sprite(self) -> QPixmap:
        if self.paused:
            return self.sprite_frames[0]

        if self.reaction_ticks_remaining > 0:
            return self.sprite_frames[1]

        if self.message:
            return self.sprite_frames[1]

        if self.movement_state == "idle":
            if self.frame % 160 > 148:
                return self.sprite_frames[1]

            return self.sprite_frames[0]

        if (self.frame // 8) % 2 == 0:
            return self.sprite_frames[2]

        return self.sprite_frames[3]

    def get_scaled_sprite(self) -> QPixmap:
        sprite = self.current_sprite()

        target_size = QSize(
            int(self.settings["sprite_width"]),
            int(self.settings["sprite_height"]),
        )

        return sprite.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    def get_sprite_rect(self, scaled_sprite, force_message=None, force_menu=None):
        has_message_layout = self.message if force_message is None else force_message
        has_menu_layout = self.menu_visible if force_menu is None else force_menu

        if has_menu_layout:
            x = (self.width() - scaled_sprite.width()) // 2
            y = (self.height() - scaled_sprite.height()) // 2
        elif has_message_layout:
            if self.last_direction >= 0:
                x = 18
            else:
                x = self.width() - scaled_sprite.width() - 18

            y = self.height() - scaled_sprite.height() - 8
        else:
            x = (self.width() - scaled_sprite.width()) // 2
            y = self.height() - scaled_sprite.height() - 8

        return QRect(x, y, scaled_sprite.width(), scaled_sprite.height())

    def point_is_on_sprite(self, point):
        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)

        padding = int(self.settings.get("sprite_click_padding", 8))
        return sprite_rect.adjusted(
            -padding,
            -padding,
            padding,
            padding,
        ).contains(point)

    def get_mouth_point(self, sprite_rect):
        if self.last_direction >= 0:
            mouth_x = sprite_rect.left() + int(sprite_rect.width() * 0.86)
        else:
            mouth_x = sprite_rect.left() + int(sprite_rect.width() * 0.14)

        mouth_y = sprite_rect.top() + int(sprite_rect.height() * 0.38)

        return QPoint(mouth_x, mouth_y)

    def get_speech_bubble_geometry(self, sprite_rect):
        if not self.message:
            return None, None

        mouth = self.get_mouth_point(sprite_rect)

        bubble_width = 125
        bubble_height = 40
        bubble_gap = 18
        bubble_vertical_offset = 62

        if self.last_direction >= 0:
            bubble_rect = QRect(
                mouth.x() + bubble_gap,
                mouth.y() - bubble_vertical_offset,
                bubble_width,
                bubble_height,
            )

            tail = QPolygon(
                [
                    mouth,
                    QPoint(bubble_rect.left() + 10, bubble_rect.bottom() - 8),
                    QPoint(bubble_rect.left() + 26, bubble_rect.bottom() - 2),
                ]
            )
        else:
            bubble_rect = QRect(
                mouth.x() - bubble_gap - bubble_width,
                mouth.y() - bubble_vertical_offset,
                bubble_width,
                bubble_height,
            )

            tail = QPolygon(
                [
                    mouth,
                    QPoint(bubble_rect.right() - 10, bubble_rect.bottom() - 8),
                    QPoint(bubble_rect.right() - 26, bubble_rect.bottom() - 2),
                ]
            )

        return bubble_rect, tail

    def get_menu_buttons(self, sprite_rect):
        if not self.menu_visible:
            return []

        center = sprite_rect.center()
        radius = int(self.settings.get("menu_arc_radius", 102))
        button_radius = int(self.settings["menu_button_radius"])

        pause_label = "Resume" if self.paused else "Pause"

        top_items = [
            ("hide", "Hide", 210),
            ("pause", pause_label, 250),
            ("reset", "Reset", 290),
            ("quit", "Quit", 330),
        ]

        bottom_items = [
            ("pet", "Pet", 30),
            ("treat", "Treat", 70),
            ("ball", "Ball", 110),
            ("talk", "Talk", 150),
        ]

        buttons = []

        for action, label, angle_degrees in top_items + bottom_items:
            angle = math.radians(angle_degrees)
            button_center_x = center.x() + int(radius * math.cos(angle))
            button_center_y = center.y() + int(radius * math.sin(angle))

            rect = QRect(
                button_center_x - button_radius,
                button_center_y - button_radius,
                button_radius * 2,
                button_radius * 2,
            )

            group = "top" if angle_degrees > 180 else "bottom"

            buttons.append(
                {
                    "action": action,
                    "label": label,
                    "rect": rect,
                    "group": group,
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

        if action == "hide":
            self.hide_temporarily()
        elif action == "pause":
            self.toggle_pause()

            if self.paused:
                self.say_random_speech("pause")
            else:
                self.say_random_speech("resume")

        elif action == "reset":
            self.reset_position()
            self.say_random_speech("reset")
        elif action == "quit":
            QApplication.quit()
        elif action == "pet":
            self.pet_nomzy()
            self.say_random_speech("pet")
        elif action == "treat":
            self.pet_nomzy()
            self.say_random_speech("treat")
        elif action == "ball":
            self.pet_nomzy()
            self.say_random_speech("ball")
        elif action == "talk":
            self.say_random_speech("talk")

    def hide_temporarily(self):
        self.save_state()
        self.hide()

        QTimer.singleShot(10000, self.restore_after_temporary_hide)

    def restore_after_temporary_hide(self):
        self.show()
        self.update_overlay_mask()
        self.apply_native_overlay_style()
        self.enforce_always_on_top()
        self.say_random_speech("hide_return")

    def reset_position(self):
        screen = QApplication.primaryScreen()
        bounds = screen.availableGeometry()

        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)

        desired_sprite_center = bounds.center()
        new_top_left = desired_sprite_center - sprite_rect.center()

        self.move(new_top_left)
        self.update_overlay_mask()
        self.enforce_always_on_top()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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

            self.drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

            self.mouse_press_global = event.globalPosition().toPoint()
            self.is_dragging = False
            event.accept()
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            if self.pending_menu_action is not None or self.close_menu_on_release:
                event.accept()
                return

            current_global = event.globalPosition().toPoint()
            moved_distance = (
                current_global - self.mouse_press_global
            ).manhattanLength()

            if moved_distance > 4:
                self.is_dragging = True
                self.move(current_global - self.drag_position)

            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
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

            if not self.is_dragging:
                local_point = event.position().toPoint()

                if self.point_is_on_sprite(local_point):
                    self.toggle_menu()

            self.is_dragging = False
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        pause_action = QAction(
            "Resume Nomzy" if self.paused else "Pause Nomzy",
            self,
        )
        pause_action.triggered.connect(self.toggle_pause)

        speak_action = QAction("Say Something Now", self)
        speak_action.triggered.connect(lambda: self.say_random_speech("talk"))

        reset_action = QAction("Reset Position", self)
        reset_action.triggered.connect(self.reset_position)

        quit_action = QAction("Quit Nomzy", self)
        quit_action.triggered.connect(QApplication.quit)

        menu.addAction(pause_action)
        menu.addAction(speak_action)
        menu.addAction(reset_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def toggle_pause(self):
        self.paused = not self.paused

    def draw_speech_bubble(self, painter, sprite_rect):
        if not self.message:
            return

        bubble_rect, tail = self.get_speech_bubble_geometry(sprite_rect)

        if bubble_rect is None or tail is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bubble_fill = QColor(
            255,
            255,
            255,
            int(self.settings["speech_bubble_opacity"]),
        )
        bubble_outline = QColor(170, 170, 170, 130)
        text_color = QColor(45, 45, 45, 225)

        painter.setPen(QPen(bubble_outline, 2))
        painter.setBrush(bubble_fill)

        painter.drawPolygon(tail)
        painter.drawRoundedRect(bubble_rect, 12, 12)

        painter.setPen(text_color)
        painter.setFont(QFont("Arial", 9))
        painter.drawText(
            bubble_rect,
            Qt.AlignmentFlag.AlignCenter,
            self.message,
        )

        painter.restore()

    def draw_menu(self, painter, sprite_rect):
        if not self.menu_visible:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        buttons = self.get_menu_buttons(sprite_rect)

        for button in buttons:
            rect = button["rect"]
            label = button["label"]
            group = button["group"]

            if group == "top":
                fill = QColor(245, 238, 255, 220)
                outline = QColor(155, 130, 190, 210)
            else:
                fill = QColor(255, 246, 230, 220)
                outline = QColor(205, 150, 90, 210)

            painter.setPen(QPen(outline, 2))
            painter.setBrush(fill)
            painter.drawEllipse(rect)

            painter.setPen(QColor(45, 45, 45, 235))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(
                rect,
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        painter.restore()

    def draw_nomzy_sprite(self, painter, scaled_sprite, sprite_rect):
        painter.save()

        if self.last_direction < 0:
            painter.translate(self.width(), 0)
            painter.scale(-1, 1)

            mirrored_x = self.width() - sprite_rect.x() - sprite_rect.width()
            draw_rect = QRect(
                mirrored_x,
                sprite_rect.y(),
                sprite_rect.width(),
                sprite_rect.height(),
            )
        else:
            draw_rect = sprite_rect

        painter.drawPixmap(draw_rect, scaled_sprite)

        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)

        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)

        if self.menu_visible:
            self.draw_menu(painter, sprite_rect)
        else:
            self.draw_speech_bubble(painter, sprite_rect)

        self.draw_nomzy_sprite(painter, scaled_sprite, sprite_rect)