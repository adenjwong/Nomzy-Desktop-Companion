import logging
import sys

from PySide6.QtWidgets import QApplication

from .application import ApplicationController
from . import __version__
from .diagnostics import configure_logging, install_error_handlers, restore_error_handlers

LOGGER = logging.getLogger(__name__)


def run(argv: list[str] | None = None) -> int:
    app = QApplication(sys.argv if argv is None else argv)
    controller = ApplicationController(app)
    try:
        if not controller.start():
            return 0
        return app.exec()
    finally:
        controller.shutdown()


def main() -> int:
    configure_logging()
    previous = install_error_handlers()
    LOGGER.info("Starting Nomzy %s (platform=%s, bundled=%s)", __version__, sys.platform, bool(getattr(sys, "frozen", False)))
    try:
        return run()
    except Exception:
        LOGGER.exception("Nomzy could not start")
        return 1
    finally:
        restore_error_handlers(previous)


if __name__ == "__main__":
    raise SystemExit(main())
