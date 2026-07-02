import math
import random
import sys

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QAction, QColor, QPainter, QPen, QBrush
from PySide6.QtWidgets import QApplication, QMenu, QWidget


class NomzyDog(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Nomzy Desktop Companion")
        self.setFixedSize(220, 180)

        # Small, transparent, always-on-top companion window.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.drag_position = QPoint()
        self.frame = 0

        self.paused = False
        self.speed_x = random.choice([-2, -1, 1, 2])
        self.speed_y = random.choice([-1, 1])

        # Controls both animation and wandering.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(40)

    def tick(self):
        self.frame += 1

        if not self.paused:
            self.wander()

        self.update()

    def wander(self):
        current_pos = self.pos()
        new_x = current_pos.x() + self.speed_x
        new_y = current_pos.y() + self.speed_y

        screen = self.screen() or QApplication.primaryScreen()
        bounds = screen.availableGeometry()

        left = bounds.left()
        right = bounds.right() - self.width()
        top = bounds.top()
        bottom = bounds.bottom() - self.height()

        if new_x <= left or new_x >= right:
            self.speed_x *= -1
            new_x = max(left, min(new_x, right))

        if new_y <= top or new_y >= bottom:
            self.speed_y *= -1
            new_y = max(top, min(new_y, bottom))

        self.move(new_x, new_y)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        pause_action = QAction(
            "Resume Wandering" if self.paused else "Pause Wandering",
            self,
        )
        pause_action.triggered.connect(self.toggle_pause)

        quit_action = QAction("Quit Nomzy", self)
        quit_action.triggered.connect(QApplication.quit)

        menu.addAction(pause_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def toggle_pause(self):
        self.paused = not self.paused

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bounce = math.sin(self.frame / 12) * 4
        y_offset = int(bounce)

        fur = QColor("#C9975B")
        fur_dark = QColor("#8B5E34")
        fur_light = QColor("#F0C987")
        nose = QColor("#2B1B12")
        eye = QColor("#1F1F1F")
        blush = QColor("#E8A0A0")

        painter.setPen(Qt.PenStyle.NoPen)

        # Shadow
        painter.setBrush(QColor(0, 0, 0, 45))
        painter.drawEllipse(50, 145, 120, 18)

        # Body
        painter.setBrush(QBrush(fur))
        painter.drawRoundedRect(55, 75 + y_offset, 110, 70, 35, 35)

        # Head
        painter.drawEllipse(55, 25 + y_offset, 110, 90)

        # Ears
        painter.setBrush(QBrush(fur_dark))
        painter.drawEllipse(43, 28 + y_offset, 38, 55)
        painter.drawEllipse(139, 28 + y_offset, 38, 55)

        # Inner ears
        painter.setBrush(QBrush(fur_light))
        painter.drawEllipse(53, 42 + y_offset, 20, 30)
        painter.drawEllipse(147, 42 + y_offset, 20, 30)

        # Face patch
        painter.drawEllipse(80, 58 + y_offset, 60, 45)

        # Eyes
        painter.setBrush(QBrush(eye))
        painter.drawEllipse(82, 57 + y_offset, 10, 12)
        painter.drawEllipse(128, 57 + y_offset, 10, 12)

        # Eye highlights
        painter.setBrush(QBrush(QColor("white")))
        painter.drawEllipse(85, 59 + y_offset, 3, 3)
        painter.drawEllipse(131, 59 + y_offset, 3, 3)

        # Nose
        painter.setBrush(QBrush(nose))
        painter.drawEllipse(103, 73 + y_offset, 14, 10)

        # Mouth
        painter.setPen(QPen(nose, 2))
        painter.drawLine(110, 82 + y_offset, 110, 90 + y_offset)
        painter.drawArc(98, 86 + y_offset, 14, 12, 0, -180 * 16)
        painter.drawArc(110, 86 + y_offset, 14, 12, 180 * 16, -180 * 16)

        # Blush
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(blush))
        painter.drawEllipse(70, 79 + y_offset, 12, 7)
        painter.drawEllipse(138, 79 + y_offset, 12, 7)

        # Legs
        painter.setBrush(QBrush(fur_dark))
        painter.drawRoundedRect(72, 125 + y_offset, 22, 28, 10, 10)
        painter.drawRoundedRect(126, 125 + y_offset, 22, 28, 10, 10)

        # Tail wag
        painter.setPen(
            QPen(
                fur_dark,
                8,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
            )
        )
        tail_wag = math.sin(self.frame / 6) * 10
        painter.drawArc(
            145,
            80 + y_offset + int(tail_wag / 4),
            45,
            40,
            20 * 16,
            180 * 16,
        )


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