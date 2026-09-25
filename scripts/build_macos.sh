#!/bin/sh
# Run from any directory. PYTHON may select a dedicated release environment.
set -eu
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3.11}"
unset PYTHONPATH PYTHONHOME QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH QT_QPA_PLATFORM
"$PYTHON" -c 'import sys; assert sys.platform == "darwin", "Build on macOS"; assert sys.version_info[:2] == (3, 11), "Use Python 3.11"'
"$PYTHON" scripts/check_build_environment.py
export PYINSTALLER_CONFIG_DIR="$PWD/build/pyinstaller-cache"
# Fail early if Qt cannot initialize (including CPU detection in sandboxes).
"$PYTHON" -c 'from PySide6.QtCore import qVersion; print("Qt", qVersion())'
"$PYTHON" -m PyInstaller --clean --noconfirm Nomzy.spec
"$PYTHON" scripts/verify_bundle.py dist/Nomzy.app
