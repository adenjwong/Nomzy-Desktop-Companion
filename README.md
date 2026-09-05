# Nomzy Desktop Companion

Nomzy is a small animated desktop companion built with PySide6.

## Requirements

- macOS
- CPython 3.11 (the only supported Python release)

The native macOS integration is installed only on macOS. Runtime state and user
settings are stored in Qt's per-user application-data directory, not in the
repository or Python environment.

## Install and run

Create a fresh virtual environment from a clone of the repository:

```shell
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .
nomzy
```

For development, use an editable install and run the test suite:

```shell
python -m pip install --editable .
QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests
```

`python -m nomzy` is also supported. Set `NOMZY_RESOURCE_ROOT` only when a
packager places the `assets` and `config` directories under a custom resource
root; ordinary repository, wheel, frozen-app, and macOS application-bundle
layouts are detected automatically.
