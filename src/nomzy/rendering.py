from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRegion,
)


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

        if self.activity.menu_open:
            for button in self.get_menu_buttons(sprite_rect):
                button_region = QRegion(
                    button["rect"],
                    QRegion.RegionType.Ellipse,
                )
                region = region.united(button_region)

        if self.message and self.settings.get("speech_bubble_blocks_input", True):
            bubble_rect, bubble_path = self.get_speech_bubble_geometry(sprite_rect)
            if bubble_rect is not None and bubble_path is not None:
                bubble_region = QRegion(
                    bubble_path.toFillPolygon().toPolygon(),
                    Qt.FillRule.WindingFill,
                )
                region = region.united(bubble_region)

        self.setMask(region)

    def current_sprite(self) -> QPixmap:
        return self.sprite_frames[self.animation_player.frame.sprite]

    def get_scaled_sprite(self) -> QPixmap:
        render_scale = self.animation_player.clip.render_scale
        target_size = QSize(
            round(int(self.settings["sprite_width"]) * render_scale),
            round(int(self.settings["sprite_height"]) * render_scale),
        )
        return self.current_sprite().scaled(
            target_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    def get_sprite_rect(self, scaled_sprite, force_message=None, force_menu=None):
        has_message_layout = self.message if force_message is None else force_message
        has_menu_layout = (
            self.activity.menu_open if force_menu is None else force_menu
        )

        if has_menu_layout:
            anchor_x = self.width() / 2
            anchor_y = self.height() / 2 + scaled_sprite.height() * (
                self.sprite_anchor_y - 0.5
            )
            x = round(anchor_x - scaled_sprite.width() * self.sprite_anchor_x)
            y = round(anchor_y - scaled_sprite.height() * self.sprite_anchor_y)
        elif has_message_layout:
            x = 18 if self.last_direction >= 0 else self.width() - scaled_sprite.width() - 18
            anchor_y = self.height() - 8
            y = round(anchor_y - scaled_sprite.height() * self.sprite_anchor_y)
        else:
            anchor_x = self.width() / 2
            anchor_y = self.height() - 8
            x = round(anchor_x - scaled_sprite.width() * self.sprite_anchor_x)
            y = round(anchor_y - scaled_sprite.height() * self.sprite_anchor_y)

        return QRect(x, y, scaled_sprite.width(), scaled_sprite.height())

    def point_is_on_sprite(self, point):
        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)
        padding = int(self.settings.get("sprite_click_padding", 8))
        return sprite_rect.adjusted(-padding, -padding, padding, padding).contains(point)

    def get_drag_anchor_point(self):
        scaled_sprite = self.get_scaled_sprite()
        sprite_rect = self.get_sprite_rect(scaled_sprite)
        return QPoint(
            sprite_rect.center().x(),
            sprite_rect.top() + round(sprite_rect.height() * 0.32),
        )

    def get_mouth_point(self, sprite_rect):
        horizontal_ratio = 0.86 if self.last_direction >= 0 else 0.14
        mouth_x = sprite_rect.left() + int(sprite_rect.width() * horizontal_ratio)
        mouth_y = sprite_rect.top() + int(sprite_rect.height() * 0.38)
        return QPoint(mouth_x, mouth_y)

    def get_speech_tail_tip(self, sprite_rect, mouth):
        tail_clearance = 12
        if self.last_direction < 0:
            return QPoint(sprite_rect.left() - tail_clearance, mouth.y() - 3)
        return QPoint(sprite_rect.right() + tail_clearance, mouth.y() - 3)

    def get_speech_bubble_geometry(self, sprite_rect):
        if not self.message:
            return None, None

        mouth = self.get_mouth_point(sprite_rect)
        bubble_width = 145
        bubble_height = 46
        bubble_gap = 28
        bubble_vertical_offset = 64

        if self.last_direction >= 0:
            bubble_rect = QRect(
                sprite_rect.right() + bubble_gap,
                mouth.y() - bubble_vertical_offset,
                bubble_width,
                bubble_height,
            )
        else:
            bubble_rect = QRect(
                sprite_rect.left() - bubble_gap - bubble_width,
                mouth.y() - bubble_vertical_offset,
                bubble_width,
                bubble_height,
            )
        tail_tip = self.get_speech_tail_tip(sprite_rect, mouth)
        return bubble_rect, self.build_speech_bubble_path(bubble_rect, tail_tip)

    def build_speech_bubble_path(self, bubble_rect, tail_tip):
        rect = QRectF(bubble_rect)
        tail_tip = QPointF(tail_tip)
        radius = 20.0
        left = rect.left()
        right = rect.right()
        top = rect.top()
        bottom = rect.bottom()
        path = QPainterPath()

        path.moveTo(left + radius, top)
        path.lineTo(right - radius, top)
        path.quadTo(right, top, right, top + radius)
        path.lineTo(right, bottom - radius)
        path.quadTo(right, bottom, right - radius, bottom)

        if self.last_direction < 0:
            path.lineTo(right - 22, bottom)
            path.cubicTo(
                right - 20,
                bottom + 8,
                tail_tip.x() - 2,
                tail_tip.y() + 1,
                tail_tip.x(),
                tail_tip.y(),
            )
            path.cubicTo(
                tail_tip.x() - 15,
                tail_tip.y() + 6,
                right - 44,
                bottom + 14,
                right - 54,
                bottom,
            )
        else:
            path.lineTo(left + 54, bottom)
            path.cubicTo(
                left + 44,
                bottom + 14,
                tail_tip.x() + 15,
                tail_tip.y() + 6,
                tail_tip.x(),
                tail_tip.y(),
            )
            path.cubicTo(
                tail_tip.x() + 2,
                tail_tip.y() + 1,
                left + 20,
                bottom + 8,
                left + 22,
                bottom,
            )

        path.lineTo(left + radius, bottom)
        path.quadTo(left, bottom, left, bottom - radius)
        path.lineTo(left, top + radius)
        path.quadTo(left, top, left + radius, top)
        path.closeSubpath()
        return path

    def draw_speech_bubble(self, painter, sprite_rect):
        if not self.message:
            return
        bubble_rect, bubble_path = self.get_speech_bubble_geometry(sprite_rect)
        if bubble_rect is None or bubble_path is None:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bubble_fill = QColor(255, 255, 255, int(self.settings["speech_bubble_opacity"]))
        shadow_path = QPainterPath(bubble_path)
        shadow_path.translate(0, 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 35))
        painter.drawPath(shadow_path)
        outline = QPen(QColor(135, 135, 135, 190), 2)
        outline.setCapStyle(Qt.PenCapStyle.RoundCap)
        outline.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(outline)
        painter.setBrush(bubble_fill)
        painter.drawPath(bubble_path)
        painter.setPen(QColor(45, 45, 45, 225))
        painter.setFont(QFont("Arial", 9))
        text_rect = bubble_rect.adjusted(8, 4, -8, -4)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.message)
        painter.restore()

    def draw_menu(self, painter, sprite_rect):
        if not self.activity.menu_open:
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
        mirror_sprite = (
            self.last_direction < 0
            and self.animation_player.clip.mirror_with_direction
        )
        if mirror_sprite:
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
        if self.activity.menu_open:
            self.draw_menu(painter, sprite_rect)
        else:
            self.draw_speech_bubble(painter, sprite_rect)
        self.draw_nomzy_sprite(painter, scaled_sprite, sprite_rect)
