from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QPolygon, QRegion


class CompanionRenderingMixin:
    """Sprite selection, layout geometry, input masking, and painting."""

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
        region = QRegion(sprite_rect.adjusted(-padding, -padding, padding, padding))

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
                region = region.united(
                    QRegion(
                        bubble_rect.adjusted(-3, -3, 3, 3),
                        QRegion.RegionType.Rectangle,
                    )
                )
            if tail is not None:
                region = region.united(QRegion(tail))

        self.setMask(region)

    def current_sprite(self) -> QPixmap:
        if self.paused:
            return self.sprite_frames[0]
        if self.reaction_ticks_remaining > 0 or self.message:
            return self.sprite_frames[1]
        if self.movement_state == "idle":
            return self.sprite_frames[1] if self.frame % 160 > 148 else self.sprite_frames[0]
        return self.sprite_frames[2] if (self.frame // 8) % 2 == 0 else self.sprite_frames[3]

    def get_scaled_sprite(self) -> QPixmap:
        target_size = QSize(
            int(self.settings["sprite_width"]),
            int(self.settings["sprite_height"]),
        )
        return self.current_sprite().scaled(
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
            x = 18 if self.last_direction >= 0 else self.width() - scaled_sprite.width() - 18
            y = self.height() - scaled_sprite.height() - 8
        else:
            x = (self.width() - scaled_sprite.width()) // 2
            y = self.height() - scaled_sprite.height() - 8

        return QRect(x, y, scaled_sprite.width(), scaled_sprite.height())

    def point_is_on_sprite(self, point):
        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)
        padding = int(self.settings.get("sprite_click_padding", 8))
        return sprite_rect.adjusted(-padding, -padding, padding, padding).contains(point)

    def get_mouth_point(self, sprite_rect):
        horizontal_ratio = 0.86 if self.last_direction >= 0 else 0.14
        mouth_x = sprite_rect.left() + int(sprite_rect.width() * horizontal_ratio)
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

    def draw_speech_bubble(self, painter, sprite_rect):
        if not self.message:
            return
        bubble_rect, tail = self.get_speech_bubble_geometry(sprite_rect)
        if bubble_rect is None or tail is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bubble_fill = QColor(255, 255, 255, int(self.settings["speech_bubble_opacity"]))
        painter.setPen(QPen(QColor(170, 170, 170, 130), 2))
        painter.setBrush(bubble_fill)
        painter.drawPolygon(tail)
        painter.drawRoundedRect(bubble_rect, 12, 12)
        painter.setPen(QColor(45, 45, 45, 225))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(bubble_rect, Qt.AlignmentFlag.AlignCenter, self.message)
        painter.restore()

    def draw_menu(self, painter, sprite_rect):
        if not self.menu_visible:
            return
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for button in self.get_menu_buttons(sprite_rect):
            if button["group"] == "top":
                fill = QColor(245, 238, 255, 220)
                outline = QColor(155, 130, 190, 210)
            else:
                fill = QColor(255, 246, 230, 220)
                outline = QColor(205, 150, 90, 210)

            painter.setPen(QPen(outline, 2))
            painter.setBrush(fill)
            painter.drawEllipse(button["rect"])
            painter.setPen(QColor(45, 45, 45, 235))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(
                button["rect"],
                Qt.AlignmentFlag.AlignCenter,
                button["label"],
            )
        painter.restore()

    def draw_nomzy_sprite(self, painter, scaled_sprite, sprite_rect):
        painter.save()
        if self.last_direction < 0:
            painter.translate(self.width(), 0)
            painter.scale(-1, 1)
            draw_rect = QRect(
                self.width() - sprite_rect.x() - sprite_rect.width(),
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
