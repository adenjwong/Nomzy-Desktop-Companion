"""Render Nomzy's existing paw mark as a macOS icon; requires PySide6 + iconutil."""
import subprocess
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QImage, QPainter


def render(size, destination):
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 1024, size / 1024)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#eadbc4"))
    painter.drawRoundedRect(QRectF(64, 64, 896, 896), 200, 200)
    painter.setBrush(QColor("#593b29"))
    # The same four-toed paw used by Nomzy's menu-bar icon.
    painter.translate(145, 140)
    painter.scale(32, 32)
    painter.drawEllipse(QRectF(4, 9, 15, 12))
    for x, y in ((2, 6), (7, 2), (13, 2), (18, 6)):
        painter.drawEllipse(QRectF(x, y, 4, 6))
    painter.end()
    if not image.save(str(destination)):
        raise RuntimeError(f"Could not write {destination}")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as directory:
        iconset = Path(directory) / "Nomzy.iconset"
        iconset.mkdir()
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                suffix = "@2x" if scale == 2 else ""
                render(size * scale, iconset / f"icon_{size}x{size}{suffix}.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o",
                        str(root / "packaging/Nomzy.icns")], check=True)
