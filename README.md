# Running Nomzy

## Install the standalone app

Requires macOS 13 or later and an Apple Silicon Mac (M1 or newer).

1. Copy `Nomzy.app` into your `Applications` folder.
2. Double-click `Nomzy` to launch it.
3. Nomzy will appear on your desktop, with a paw icon in the menu bar.

If macOS blocks the app, go to **System Settings → Privacy & Security**, select **Open Anyway**, and confirm.

To launch Nomzy later, open it from `Applications` or search for `Nomzy` in Spotlight.

## Install and run from source

Requires macOS. Choose either Conda or Python's built-in virtual environment.

First, open Terminal and navigate to the project folder, replacing the path below with its actual location:

```shell
cd /path/to/Nomzy-Desktop-Companion
```

### Option 1: Conda

Requires Conda, available through Miniconda or Anaconda.

Create the environment using `environment.yml`. This installs Python 3.11, Nomzy, and its dependencies:

```shell
conda env create -f environment.yml
conda activate nomzy
nomzy
```

To run Nomzy again in a new Terminal window:

```shell
conda activate nomzy
nomzy
```

### Option 2: Python and requirements.txt

Requires Python 3.11.

Create and activate a virtual environment, install the dependencies and Nomzy, then launch the app:

```shell
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install --editable .
nomzy
```

To run Nomzy again in a new Terminal window, return to the project folder and activate the environment:

```shell
cd /path/to/Nomzy-Desktop-Companion
source .venv/bin/activate
nomzy
```