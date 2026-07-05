from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPixmap

from .paths import get_sprite_sheet_path


def load_sprite_frames() -> list[QPixmap]:
    sprite_path = get_sprite_sheet_path()

    if not sprite_path.exists():
        raise FileNotFoundError(
            f"Missing sprite sheet: {sprite_path}\n"
            "Expected file location: assets/nomzy_sprite_sheet.png"
        )

    sheet = QPixmap(str(sprite_path))

    if sheet.isNull():
        raise RuntimeError(f"Could not load sprite sheet: {sprite_path}")

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

        frames.append(trim_transparent_space(raw_frame))

    return frames


def trim_transparent_space(pixmap: QPixmap) -> QPixmap:
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