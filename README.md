# Nomzy Desktop Companion

Nomzy is a small animated dog that lives on your Mac desktop. It walks, blinks,
rests, and shares little thoughts. Click Nomzy to open its menu, drag to pick it
up, or use the paw in your menu bar to find it and open Settings. Nomzy also
wears a party hat on September 29.

**0.9.0 is the feature-complete beta.** The intended 1.0 feature set is frozen;
remaining beta work focuses on bugs, stability, usability, and release testing.

## Install the beta

Requires an Apple silicon Mac (M1 or newer) running macOS 13 or later. Intel
builds are not available. Minimum-OS and separate-account testing are still
pending.

1. Get `Nomzy-0.9.0-macOS-arm64.zip` from your beta invitation or the project's
   [Releases page](https://github.com/adenjwong/Nomzy-Desktop-Companion/releases)
   when published.
2. Double-click the ZIP to extract it.
3. Drag `Nomzy.app` into Applications and open that copy.

No Python, Terminal, or repository is required. Nomzy appears with a paw icon in
the menu bar. This candidate is ad-hoc signed and is not notarized. If macOS
blocks it, try opening it and then use **System Settings → Privacy & Security →
Open Anyway**, following macOS's prompts. Only open a copy from a trusted source.

## Use Nomzy

- Click the dog for **Pet**, **Treat**, **Ball**, **Talk**, **Pause**, **Reset**,
  **Settings**, and **Quit**. Click Nomzy again to close the menu.
- Drag the dog to move it. It stays within the usable area of your displays.
- The menu-bar paw provides **Show / Locate Nomzy**, **Pause / Resume Nomzy**,
  **Settings**, **Reset Position**, **About Nomzy**, and **Quit Nomzy**.
- Pause stops autonomous activity; a current speech bubble still expires.
  Manual interactions remain available.
- Settings changes take effect with **Apply**. **Cancel** or closing discards
  unapplied edits. **Restore Defaults** prepares defaults until you click Apply.
  **Launch at Login** takes effect immediately and is separate from Apply/Cancel.

## Settings and defaults

| Setting | Default |
| --- | --- |
| Your name | Blank (Nomzy calls you “friend”) |
| Nomzy size | 110 × 85 pixels |
| Always on top / Remember position | On / On |
| Launch at Login | Off on a fresh installation; managed by macOS |
| Enable movement | On |
| Walk about every / Movement amount | 5 seconds / Normal (0.4–1.4 second walks) |
| Rest interval / Sleep chance | 45–120 seconds / 30% |
| Blink interval | 6–12 seconds |
| Enable autonomous speech | On (Talk also works when off) |
| Speaking interval / Bubble display time | 60–180 seconds / 3–5 seconds |
| Bubble opacity | 60% |

Intervals are approximate and pause during other activities. Existing preferences
are retained on upgrade. Restore Defaults does not unregister Launch at Login.

## Update or uninstall

Quit using the menu-bar paw, extract the new ZIP, drag the app into Applications,
and choose **Replace**. Settings are preserved. Check your running version under
**About Nomzy**.

To uninstall, turn off **Launch at Login**, quit, and move the app to Trash.
Your preferences remain for reinstalling. See [installation details](packaging/INSTALLATION.md)
for backups, legacy migration, and optional preference/log removal.

## Help and beta feedback

If Nomzy is missing, choose **Show / Locate Nomzy** or **Reset Position** from the
paw. If it is frozen, quit and reopen it. A second launch uses the existing
instance. If launch at login needs approval, check **System Settings → General →
Login Items** and the status shown in Nomzy Settings.

[Report a problem](https://github.com/adenjwong/Nomzy-Desktop-Companion/issues)
with your Nomzy version (About), macOS version, Mac model, steps to reproduce,
expected/actual behavior, and a screenshot if helpful. Logs are in
`~/Library/Logs/Nomzy/nomzy.log`; review them before sharing. Preferences are in
`~/Library/Application Support/Nomzy/Nomzy Desktop Companion/`.

## Run from source

Development requires Python 3.11. From the project folder:

```shell
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install --editable .
nomzy
```

Or use `conda env create -f environment.yml`, `conda activate nomzy`, then `nomzy`.
For later runs, activate the same environment and run `nomzy`.

## Build a macOS release

On a native Apple silicon Mac with Python 3.11:

```shell
python3.11 -m venv .venv-build
.venv-build/bin/python -m pip install -r packaging/requirements-build.txt
.venv-build/bin/python -m pip install --no-deps --editable .
PYTHON=.venv-build/bin/python sh scripts/build_macos.sh
```

The pinned build produces `dist/Nomzy.app`, a versioned ZIP, and a SHA-256 file.
It verifies signing, resources, architecture, relocation, and archive extraction.
See [packaging validation](packaging/VALIDATION.md) for scope and known limitations.
