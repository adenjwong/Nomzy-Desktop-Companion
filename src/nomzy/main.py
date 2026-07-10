import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication


CURRENT_FILE = Path(__file__).resolve()
SRC_DIR = CURRENT_FILE.parents[1]

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from nomzy.companion import NomzyDog  # noqa: E402
from nomzy.macos_overlay import configure_macos_application  # noqa: E402


def main():
    app = QApplication(sys.argv)

    configure_macos_application(hide_dock_icon=True)

    nomzy = NomzyDog()
    app.aboutToQuit.connect(nomzy.save_state)

    saved_position = nomzy.get_saved_position()

    if saved_position is not None:
        nomzy.move(saved_position)
    else:
        screen = QApplication.primaryScreen()
        bounds = screen.availableGeometry()

        start_x = bounds.center().x()
        start_y = bounds.center().y()

        nomzy.move(start_x, start_y)

    nomzy.show()
    nomzy.apply_native_overlay_style()
    nomzy.enforce_always_on_top()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()