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

## Settings (0.6.0)

Open **Settings** from Nomzy's menu or right-click menu:

- **General:** your name, Nomzy's size, always on top, and remembering position.
- **Movement:** enable walking, choose how often to walk, and select Low, Normal,
  or High movement amounts. Existing custom amounts are preserved.
- **Idle behavior:** minimum and maximum time between rests and blinks, and the
  chance that a rest becomes sleep instead of sitting.
- **Speech:** autonomous speech, minimum and maximum speaking intervals, bubble
  display time, and bubble opacity. Manual speech remains available when
  autonomous speech is disabled.

Intervals use seconds, and opacity uses whole percentages from 10% to 100%, with
a default of 60%. Changing either end of an
interval adjusts the other end when needed to keep the range valid.

**Apply** saves and updates Nomzy immediately, with an on-screen confirmation.
**Cancel**, Escape, or closing the window discards edits since the last Apply.
**Restore Defaults** prepares defaults for the visible controls; choose Apply to
save them or Cancel to discard them. Internal overlay settings are preserved.
Changes to intervals update only their corresponding countdowns; other behavior
and animation timers continue running.

Launch at login is not yet implemented. Native macOS overlay levels and other
internal window settings are intentionally kept out of the ordinary interface.
