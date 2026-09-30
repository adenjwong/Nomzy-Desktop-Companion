"""The little party hat Nomzy wears on September 29, in local time."""

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap, QRegion


def is_party_day(today: date | None = None) -> bool:
    today = date.today() if today is None else today
    return (today.month, today.day) == (9, 29)


# Code-native pixel art: lavender cone, gold confetti, and a gold pom-pom.
HAT_PIXELS = (
    "     GG      ",
    "    GYYG     ",
    "     GG      ",
    "     PP      ",
    "    PLLP     ",
    "    PLLP     ",
    "   PLLDPP    ",
    "   PLYYDP    ",
    "  PLLYYDPP   ",
    "  PLLLDDDP   ",
    " PLLGDDLDDP  ",
    " PLLDDDLLDP  ",
    "PGGGGGGGGGGP ",
    " YYYYYYYYYY  ",
)
HAT_COLORS = {
    "P": "#76509b", "L": "#c99bea", "D": "#a876cb",
    "G": "#efb84d", "Y": "#ffe39a",
}


def with_party_hat(sprite: QPixmap, source: QPixmap) -> QPixmap:
    """Keep the dog's size and foot position, adding headroom for the hat.

    All bundled poses face right and have their ears at the top of the trimmed
    frame. The upper ear band locates the crown even when sitting or lying down.
    Compose before direction mirroring so the hat travels with Nomzy.
    """
    ear_band = source.copy(0, 0, source.width(), max(1, round(source.width() * .05)))
    ears = QRegion(ear_band.mask()).boundingRect()
    crown_x = (ears.x() + ears.width() / 2) / source.width() * sprite.width()
    unit = max(1, round(sprite.width() / 65))
    hat_width = len(HAT_PIXELS[0]) * unit
    hat_height = len(HAT_PIXELS) * unit
    # Find actual fur between the ears instead of estimating from body width.
    # Sleep and carried poses have different head proportions.
    source_image = source.toImage()
    head_x = max(0, min(source.width() - 1, round(ears.x() + ears.width() / 2)))
    head_y = next((y for y in range(source.height())
                   if source_image.pixelColor(head_x, y).alpha() > 128), 0)
    crown_y = round(head_y / source.height() * sprite.height()) + 2 * unit
    padding = max(0, hat_height + 3 * unit - crown_y)
    result = QPixmap(sprite.width(), sprite.height() + padding)
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.drawPixmap(0, padding, sprite)
    # Pivot at the brim, tucked into the fur, with a playful backward lean.
    painter.translate(crown_x, padding + crown_y)
    painter.rotate(-14)
    left = -hat_width / 2
    top = -hat_height
    for y, row in enumerate(HAT_PIXELS):
        for x, pixel in enumerate(row):
            if pixel in HAT_COLORS:
                painter.fillRect(round(left + x * unit), top + y * unit, unit, unit,
                                 QColor(HAT_COLORS[pixel]))
    painter.end()
    return result
