"""Bounded, quiet diagnostics for a windowed application."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from PySide6.QtCore import QtMsgType, qInstallMessageHandler


LOGGER = logging.getLogger(__name__)


def get_log_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / "Nomzy"
    from .paths import get_user_data_dir
    return get_user_data_dir() / "logs"


def configure_logging() -> None:
    # A full disk or unwritable log directory must not produce stderr tracebacks.
    logging.raiseExceptions = False
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_nomzy_handler", False):
            root.removeHandler(handler)
            handler.close()
    try:
        directory = get_log_dir()
        directory.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(directory / "nomzy.log", maxBytes=256 * 1024,
                                      backupCount=2, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    except OSError:
        handler = logging.NullHandler()
    handler._nomzy_handler = True
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def log_unhandled_exception(exception_type, exception, traceback):
    LOGGER.error("Unhandled application callback", exc_info=(exception_type, exception, traceback))


def log_qt_message(kind, context, message):
    level = {QtMsgType.QtDebugMsg: logging.DEBUG, QtMsgType.QtInfoMsg: logging.INFO,
             QtMsgType.QtWarningMsg: logging.WARNING}.get(kind, logging.ERROR)
    logging.getLogger("nomzy.qt").log(level, "%s", message)


def install_error_handlers():
    previous_hook = sys.excepthook
    sys.excepthook = log_unhandled_exception
    previous_qt = qInstallMessageHandler(log_qt_message)
    return previous_hook, previous_qt


def restore_error_handlers(previous):
    sys.excepthook = previous[0]
    qInstallMessageHandler(previous[1])
