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
