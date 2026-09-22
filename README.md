# Running Nomzy

## Standalone app (0.8.0)

Copy `Nomzy.app` to `/Applications`, then double-click it in Finder or search for
Nomzy in Spotlight. Python is not required. Nomzy appears as a desktop companion
and menu-bar paw; it does not open Terminal or show a Dock icon by default.

Requires macOS 13 or later. Builds target the build machine's architecture
(Apple silicon or Intel). Development builds are ad-hoc signed, not notarized.
For a downloaded build, macOS may require approval in Privacy & Security.

Settings and position live in
`~/Library/Application Support/Nomzy/Nomzy Desktop Companion/`.
Replace the app when upgrading; keep that user-data directory to retain settings.

## Run from source

Requires macOS and Python 3.11. Run these commands from the project directory:

```shell
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --editable .
nomzy
```

To run again later:

```shell
source .venv/bin/activate
nomzy
```

You can also use `python -m nomzy`.

## Build and run the macOS app

From a clean checkout on macOS, create a separate Python 3.11 build environment:

```shell
python3.11 -m venv .venv-build
.venv-build/bin/python -m pip install -r packaging/requirements-build.txt
PYTHON="$PWD/.venv-build/bin/python" sh scripts/build_macos.sh
open dist/Nomzy.app
```

The build bundles Python, Qt/PySide6, PyObjC, animation artwork, speech and default
settings. It verifies metadata and signing, then tests a relocated copy with no
development environment variables. The committed icon can be regenerated with
`.venv-build/bin/python scripts/build_icon.py`.

See [packaging validation](packaging/VALIDATION.md) for release acceptance checks.

## Recovery and diagnostics

Nomzy keeps a small rotating log at `~/Library/Logs/Nomzy/nomzy.log` on macOS
(up to three 256 KiB files). Startup and error details are recorded there without
opening a terminal. If bundled artwork is damaged, a built-in paw keeps the
companion usable; reinstall Nomzy to restore its normal animations.

Launch at Login reflects macOS settings. If approval is required, open System
Settings → General → Login Items. Before shipping, verify a real logout/login
cycle with Launch at Login both enabled and disabled, including macOS session
restoration, and confirm only one companion starts.
