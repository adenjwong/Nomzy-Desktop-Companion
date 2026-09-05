import logging
import sys

from PySide6.QtWidgets import QApplication

from . import __version__
from .companion import NomzyDog
from .macos_overlay import configure_macos_application
from .paths import APPLICATION_NAME, ORGANIZATION_NAME


LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def run(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setApplicationName(APPLICATION_NAME)
    app.setApplicationDisplayName("Nomzy")
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)

    nomzy = NomzyDog()
    configure_macos_application(
        hide_dock_icon=bool(nomzy.settings.get("macos_hide_dock_icon", True))
    )
    app.aboutToQuit.connect(nomzy.save_state)

    saved_position = nomzy.get_saved_position()

    if saved_position is not None:
        nomzy.move(saved_position)
    else:
        centered_position = nomzy.get_centered_position()
        if centered_position is not None:
            nomzy.move(centered_position)

    nomzy.show()
    nomzy.apply_native_overlay_style()
    nomzy.enforce_always_on_top()

    return app.exec()


def main() -> int:
    configure_logging()
    try:
        return run()
    except Exception:
        LOGGER.exception("Nomzy could not start")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
