import logging
import sys

from PySide6.QtWidgets import QApplication

from .application import ApplicationController

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


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
    try:
        return run()
    except Exception:
        LOGGER.exception("Nomzy could not start")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
