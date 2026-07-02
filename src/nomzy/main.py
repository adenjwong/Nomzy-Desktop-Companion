import random
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, QTimer, Qt
from PySide6.QtGui import QAction, QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QWidget


class NomzyDog(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Nomzy Desktop Companion")

        # The window is a little taller than the sprite so the speech bubble has space.
        self.setFixedSize(220, 170)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)

        # Mouse/drag state
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
        # 25 ticks = about 1 second.
        self.speech_cooldown_ticks = 25

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

        # Force a first speech bubble after launch so we know it works.
        QTimer.singleShot(1000, self.say_random_message)

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

        # Uncomment this for debugging if needed.
        # print(f"Nomzy says: {self.message}")

        # Show message for about 3–5 seconds.
        self.message_ticks_remaining = random.randint(75, 125)

        # After the message disappears, wait before speaking again.
        # 500 ticks = about 20 seconds.
        # 1800 ticks = about 72 seconds.
        self.speech_cooldown_ticks = random.randint(500, 1800)

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

    def draw_speech_bubble(self, painter):
        if not self.message:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bubble_rect = QRect(18, 8, 184, 46)

        bubble_fill = QColor(245, 238, 255, 245)
        bubble_outline = QColor("#7B5FA3")
        text_color = QColor("#2F2538")

        painter.setPen(QPen(bubble_outline, 2))
        painter.setBrush(bubble_fill)
        painter.drawRoundedRect(bubble_rect, 11, 11)

        # Bubble tail
        painter.setPen(QPen(bubble_outline, 2))
        painter.setBrush(bubble_fill)
        painter.drawPolygon(
            [
                QPoint(96, 53),
                QPoint(112, 53),
                QPoint(102, 66),
            ]
        )

        painter.setPen(text_color)
        painter.setFont(QFont("Arial", 10))
        painter.drawText(
            bubble_rect,
            Qt.AlignmentFlag.AlignCenter,
            self.message,
        )

        painter.restore()

    def draw_nomzy_sprite(self, painter):
        sprite = self.current_sprite()

        # Controls Nomzy's visual size.
        target_size = QSize(110, 85)

        scaled_sprite = sprite.scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

        x = (self.width() - scaled_sprite.width()) // 2
        y = self.height() - scaled_sprite.height() - 6

        painter.save()

        # Sprite faces right by default.
        # Flip him when his last movement was left.
        if self.last_direction < 0:
            painter.translate(self.width(), 0)
            painter.scale(-1, 1)
            x = self.width() - x - scaled_sprite.width()

        painter.drawPixmap(x, y, scaled_sprite)

        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)

        # Draw bubble first, then Nomzy.
        # These are separate so flipping the sprite does not flip the bubble.
        self.draw_speech_bubble(painter)
        self.draw_nomzy_sprite(painter)


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