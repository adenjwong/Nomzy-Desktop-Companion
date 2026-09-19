# Running Nomzy

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

With the virtual environment activated:

```shell
python -m pip install 'pyinstaller>=6,<7'
python -m PyInstaller Nomzy.spec
open dist/Nomzy.app
```

## Recovery and diagnostics

Nomzy keeps a small rotating log at `~/Library/Logs/Nomzy/nomzy.log` on macOS
(up to three 256 KiB files). Startup and error details are recorded there without
opening a terminal. If bundled artwork is damaged, a built-in paw keeps the
companion usable; reinstall Nomzy to restore its normal animations.

Launch at Login reflects macOS settings. If approval is required, open System
Settings → General → Login Items. Before shipping 0.7.2, verify a real logout/login
cycle with Launch at Login both enabled and disabled, including macOS session
restoration, and confirm only one companion starts.
