"""PySide6 initialization imports QtNetwork; Nomzy does not use OpenSSL.

Retain Qt's system-native networking dependencies, without collecting optional
OpenSSL libraries from the build environment.
"""
from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
binaries = [(source, destination) for source, destination in binaries
            if Path(source).name != "libqopensslbackend.dylib"]
