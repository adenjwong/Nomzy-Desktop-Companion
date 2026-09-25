"""Keep Qt's standard discovery except unused PDF and virtual keyboard plugins.

Filtering here, before binary dependency traversal, avoids pulling QtPdf into
the bundle. PNG artwork decoding is built into QtGui.
"""
from pathlib import Path

from PyInstaller.utils.hooks.qt import add_qt6_dependencies

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
binaries = [(source, destination) for source, destination in binaries
            if Path(source).name not in {"libqpdf.dylib", "libqtvirtualkeyboardplugin.dylib"}]
