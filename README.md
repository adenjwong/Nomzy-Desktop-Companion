# Running Nomzy

## Install

Requires macOS 13 or later and an Apple Silicon Mac (M1 or newer).

1. Download and extract the release ZIP.
2. Drag `Nomzy.app` into `Applications` and open it.

Nomzy appears on your desktop with a paw icon in the menu bar. If macOS blocks
it, open **System Settings → Privacy & Security → Open Anyway**.

Every September 29, Nomzy wears a little purple and gold party hat. He follows
your computer's local date and changes back at midnight, even while running.

## Update

Quit Nomzy, extract the new ZIP, and drag the app into `Applications`, choosing
**Replace**. Your settings are preserved. Check your version under the menu-bar
paw → **About Nomzy**.

## Uninstall

Turn off **Launch at Login** in Settings, quit Nomzy, and move the app to Trash.
Your settings are kept for reinstalling.

For migration from older source versions or optional user-data removal, see
[installation details](packaging/INSTALLATION.md).

## Run from source

From the project folder, choose one setup method:

**Conda**

```shell
conda env create -f environment.yml
conda activate nomzy
nomzy
```

**Python 3.11**

```shell
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install --editable .
nomzy
```

For later runs, activate the same environment and run `nomzy`.
