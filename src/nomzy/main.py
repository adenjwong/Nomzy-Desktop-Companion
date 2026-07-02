import random
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, QTimer, Qt
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QImage,
    QPainter,
    QPen,
    QPixmap,
    QPolygon,
)
from PySide6.QtWidgets import QApplication, QMenu, QWidget


class NomzyDog(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Nomzy Desktop Companion")

        # Wider transparent window so the speech bubble can sit diagonally
        # from Nomzy's mouth without getting clipped.
        self.setFixedSize(360, 190)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)

        # Mouse / drag state
        self.drag_position = QPoint()
        self.mouse_press_global = QPoint()
        self.is_dragging = False

        # Animation state
        self.frame = 0
        self.paused = False

        # Movement state
        self.movement_state = "idle"
        self.idle_ticks_remaining = random.randint(120, 400)
        self.walk_ticks_remaining = 0
        self.walk_step_x = 0
        self.walk_step_y = 0
        self.last_direction = 1

        # Speech state
        self.message = ""
        self.message_ticks_remaining = 0

        # Timer runs every 40 ms.
        # 1500 ticks ≈ 60 seconds
        # 4500 ticks ≈ 180 seconds
        self.speech_cooldown_ticks = random.randint(1500, 4500)

        self.messages = [
            "woof!",
            "hi!",
            "still here!",
            "good job!",
            "sniff sniff",
            "tail wag!",
            "hmm...",
            "doing great!",
            "hello!",
            "tiny steps!",
        ]

        # Click reaction state
        self.reaction_ticks_remaining = 0

        self.sprite_frames = self.load_sprite_frames()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(40)

    def load_sprite_frames(self):
        repo_root = Path(__file__).resolve().parents[2]
        sprite_path = repo_root / "assets" / "nomzy_sprite_sheet.png"

        if not sprite_path.exists():
            raise FileNotFoundError(
                f"Missing sprite sheet: {sprite_path}\n"
                "Expected file location: assets/nomzy_sprite_sheet.png"
            )

        sheet = QPixmap(str(sprite_path))

        frame_count = 4
        frame_width = sheet.width() // frame_count
        frame_height = sheet.height()

        frames = []

        for i in range(frame_count):
            raw_frame = sheet.copy(
                i * frame_width,
                0,
                frame_width,
                frame_height,
            )
            cropped_frame = self.trim_transparent_space(raw_frame)
            frames.append(cropped_frame)

        return frames

    def trim_transparent_space(self, pixmap):
        image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)

        min_x = image.width()
        min_y = image.height()
        max_x = 0
        max_y = 0
        found_pixel = False

        for y in range(image.height()):
            for x in range(image.width()):
                if image.pixelColor(x, y).alpha() > 10:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)
                    found_pixel = True

        if not found_pixel:
            return pixmap

        padding = 6

        min_x = max(0, min_x - padding)
        min_y = max(0, min_y - padding)
        max_x = min(image.width() - 1, max_x + padding)
        max_y = min(image.height() - 1, max_y + padding)

        crop_rect = QRect(
            min_x,
            min_y,
            max_x - min_x + 1,
            max_y - min_y + 1,
        )

        return pixmap.copy(crop_rect)

    def tick(self):
        self.frame += 1

        if not self.paused:
            self.update_movement()
            self.update_random_speech()

        if self.reaction_ticks_remaining > 0:
            self.reaction_ticks_remaining -= 1

        self.update()

    def update_random_speech(self):
        if self.message_ticks_remaining > 0:
            self.message_ticks_remaining -= 1

            if self.message_ticks_remaining <= 0:
                self.message = ""

            return

        self.speech_cooldown_ticks -= 1

        if self.speech_cooldown_ticks <= 0:
            self.say_random_message()

    def say_random_message(self):
        self.message = random.choice(self.messages)

        # Show message for about 3–5 seconds.
        self.message_ticks_remaining = random.randint(75, 125)

        # Talk roughly every 1–3 minutes.
        self.speech_cooldown_ticks = random.randint(1500, 4500)

        self.update()

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
        self.walk_ticks_remaining = random.randint(10, 35)

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
        self.idle_ticks_remaining = random.randint(120, 400)

    def pet_nomzy(self):
        # Clicking Nomzy gives a happy visual reaction but does not force speech.
        self.reaction_ticks_remaining = 35

        self.movement_state = "idle"
        self.walk_ticks_remaining = 0
        self.walk_step_x = 0
        self.walk_step_y = 0
        self.idle_ticks_remaining = random.randint(160, 420)

    def current_sprite(self):
        if self.paused:
            return self.sprite_frames[0]

        if self.reaction_ticks_remaining > 0:
            return self.sprite_frames[1]

        if self.message:
            return self.sprite_frames[1]

        if self.movement_state == "idle":
            # Mostly standing, with occasional blink/wag.
            if self.frame % 160 > 148:
                return self.sprite_frames[1]

            return self.sprite_frames[0]

        # Walking frames only while moving.
        return self.sprite_frames[2] if (self.frame // 8) % 2 == 0 else self.sprite_frames[3]

    def get_scaled_sprite(self):
        sprite = self.current_sprite()

        target_size = QSize(110, 85)

        return sprite.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    def get_sprite_rect(self, scaled_sprite):
        x = (self.width() - scaled_sprite.width()) // 2
        y = self.height() - scaled_sprite.height() - 8

        return QRect(x, y, scaled_sprite.width(), scaled_sprite.height())

    def get_mouth_point(self, sprite_rect):
        # Approximate mouth location based on the sprite's bounding box.
        # The original sprite faces right.
        if self.last_direction >= 0:
            mouth_x = sprite_rect.left() + int(sprite_rect.width() * 0.86)
        else:
            mouth_x = sprite_rect.left() + int(sprite_rect.width() * 0.14)

        mouth_y = sprite_rect.top() + int(sprite_rect.height() * 0.38)

        return QPoint(mouth_x, mouth_y)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

            self.mouse_press_global = event.globalPosition().toPoint()
            self.is_dragging = False
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
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
            if not self.is_dragging:
                self.pet_nomzy()

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
        speak_action.triggered.connect(self.say_random_message)

        quit_action = QAction("Quit Nomzy", self)
        quit_action.triggered.connect(QApplication.quit)

        menu.addAction(pause_action)
        menu.addAction(speak_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def toggle_pause(self):
        self.paused = not self.paused

    def draw_speech_bubble(self, painter, sprite_rect):
        if not self.message:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        mouth = self.get_mouth_point(sprite_rect)

        bubble_width = 125
        bubble_height = 40
        bubble_gap = 16
        bubble_vertical_offset = 64

        if self.last_direction >= 0:
            # Bubble sits up-right from the mouth.
            bubble_rect = QRect(
                mouth.x() + bubble_gap,
                mouth.y() - bubble_vertical_offset,
                bubble_width,
                bubble_height,
            )

            # Tail points directly to mouth.
            tail = QPolygon(
                [
                    mouth,
                    QPoint(bubble_rect.left() + 10, bubble_rect.bottom() - 8),
                    QPoint(bubble_rect.left() + 26, bubble_rect.bottom() - 2),
                ]
            )
        else:
            # Bubble sits up-left from the mouth.
            bubble_rect = QRect(
                mouth.x() - bubble_gap - bubble_width,
                mouth.y() - bubble_vertical_offset,
                bubble_width,
                bubble_height,
            )

            # Tail points directly to mouth.
            tail = QPolygon(
                [
                    mouth,
                    QPoint(bubble_rect.right() - 10, bubble_rect.bottom() - 8),
                    QPoint(bubble_rect.right() - 26, bubble_rect.bottom() - 2),
                ]
            )

        # Safety clamp so the bubble stays inside the transparent window.
        if bubble_rect.left() < 6:
            bubble_rect.moveLeft(6)

        if bubble_rect.right() > self.width() - 6:
            bubble_rect.moveRight(self.width() - 6)

        if bubble_rect.top() < 6:
            bubble_rect.moveTop(6)

        # White and more transparent.
        bubble_fill = QColor(255, 255, 255, 145)
        bubble_outline = QColor(170, 170, 170, 130)
        text_color = QColor(45, 45, 45, 225)

        painter.setPen(QPen(bubble_outline, 2))
        painter.setBrush(bubble_fill)

        # Draw the tail first so the dog sprite can cover the mouth-side point.
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

        self.draw_speech_bubble(painter, sprite_rect)
        self.draw_nomzy_sprite(painter, scaled_sprite, sprite_rect)


def main():
    app = QApplication(sys.argv)

    nomzy = NomzyDog()

    screen = QApplication.primaryScreen()
    bounds = screen.availableGeometry()

    start_x = bounds.center().x()
    start_y = bounds.center().y()

    nomzy.move(start_x, start_y)
    nomzy.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()