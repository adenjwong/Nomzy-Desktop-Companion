#!/bin/sh
# Run from any directory. PYTHON may select a dedicated release environment.
set -eu
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3.11}"
"$PYTHON" -c 'import sys; assert sys.platform == "darwin", "Build on macOS"; assert sys.version_info[:2] == (3, 11), "Use Python 3.11"'
export PYINSTALLER_CONFIG_DIR="$PWD/build/pyinstaller-cache"
"$PYTHON" -m PyInstaller --clean --noconfirm Nomzy.spec
"$PYTHON" scripts/verify_bundle.py dist/Nomzy.app
