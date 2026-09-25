# 0.8.1 packaging acceptance

Build on macOS using the pinned dependencies and commands in the README.
The build uses PyInstaller's windowed `.app` format and ad-hoc signing; Developer
ID signing, notarization and a universal binary are separate release work.
The declared minimum OS is macOS 13; test that OS before advertising compatibility.

## Bundle repair policy

- Ship architecture-specific builds. Build arm64 with native Apple silicon
  Python and x86_64 with native Intel Python. Do not merge thin apps with `lipo`:
  every Python extension, Qt framework and plugin would need compatible slices.
  Intel is not verified until the same checks pass on Intel hardware.
- Pin the entire packaging dependency set, including hooks, and reject drift.
  Python 3.11 patch version and macOS version must be recorded with results.
- Collect only animation PNGs, the manifest and the two default configuration
  files. Strip native debug symbols before signing. Omit unused Qt translations,
  PDF decoding, virtual keyboard and optional OpenSSL libraries/plugins.
- Verify every Mach-O architecture and load command, internal symlinks, source
  and development-file exclusions, and paths in both loose and compressed files.
  Vendor Qt and Conda source paths embedded in diagnostic strings are explicitly
  recognized. They are not library/resource lookup dependencies, but they mean
  the literal requirement of *zero absolute build-machine strings* remains open.
  Meeting that stronger requirement requires rebuilding the vendor dependencies
  with source-prefix mapping; this release does not rewrite vendor binaries.
  Conda Python also retains its compiled default environment prefix; the probe
  asserts that both actual Python prefixes resolve inside the relocated app.
  `scripts/verify_bundle.py --strict-build-paths` enforces the literal zero-path
  gate and currently fails. Do not mark the full 0.8.1 checklist complete yet.
- Run `scripts/repeat_bundle_build.py` with the release Python. It builds from
  two fresh source directories without existing build outputs, checks both
  relocated runtimes, and compares payload inventories. This is functional
  reproducibility, not a byte-identical-build claim.

## Automated checks

- Run `PYTHONPATH=src QT_QPA_PLATFORM=offscreen .venv-build/bin/python -m unittest discover -s tests`.
- Build from a clean checkout with no previous `build` or `dist` directory.
- `scripts/build_macos.sh` runs `scripts/verify_bundle.py` after packaging. It
  validates metadata, the ICNS icon, code-signature integrity, absence of saved
  user state, a relocated app's embedded Python runtime, all animation frames,
  speech data, default settings, Cocoa and ServiceManagement imports, and user
  settings/state paths outside the bundle. The probe does not change user data.
- Run `.venv-build/bin/python scripts/bundled_startup_smoke.py` after quitting
  existing Nomzy instances. It tests startup, duplicate launch, clean termination
  and relaunch from an unrelated working directory.

Qt's CPU detection and the Cocoa plugin need a normal macOS execution environment;
some restricted sandboxes block these even on supported Macs. A successful
PyInstaller exit alone is insufficient: the relocated-runtime check must pass.

## Interactive acceptance

1. Copy the app to `/Applications`. Launch it by double-clicking in Finder.
   Confirm the companion and menu-bar paw appear with no Terminal window.
2. Quit from the menu bar, then launch using Spotlight. Confirm one companion.
3. Open Settings; change and save a preference. Quit, replace the application
   with the candidate build, and relaunch. Confirm the preference survives.
4. Test on a separate macOS account without Python, Conda or this checkout.
   Confirm every animation and speech interaction works, and Settings persist
   across quit/relaunch. Repeat on the minimum supported OS and each architecture
   distributed to users.
5. Carry forward the login-item and Spaces acceptance checks from prior releases.

Record which checks actually ran; a sanitized process environment is useful
evidence but does not replace testing a separate account or older macOS version.

## Candidate verification — 2026-09-22

- Built 0.8.0 from a clean temporary Git checkout of the candidate sources,
  using an isolated Python 3.11 environment and the pinned release dependencies.
- Relocated-runtime verification passed: 24 frames, 11 clips, 9 speech categories,
  embedded Python 3.11.15, Cocoa and ServiceManagement. No external non-system
  absolute Mach-O dependencies were found; inspected LC_BUILD_VERSION minimums
  were at most macOS 12.0 (the app requires 13.0 for its login-item API).
- Installed the Apple silicon candidate at `/Applications/Nomzy.app`.
  Startup, duplicate-launch prevention, SIGTERM shutdown and relaunch passed
  against that copy with no stderr output. Bundle signature validation passed.
- All 156 unit tests passed. Persistence coverage checks that replacing bundled
  defaults preserves existing saved settings unchanged.
- Finder/Spotlight interaction remains pending because Computer Use permissions
  were unavailable. A separate macOS account, an actual upgrade through Finder,
  macOS 13 hardware/VM and Intel hardware were not tested. No distribution tag,
  Developer ID signing or notarization was performed.

## 0.8.1 candidate verification — 2026-09-25

- Apple silicon, macOS 26.6.2, Python 3.11.15, pinned dependencies.
- Bundle reduced from approximately 104 MiB to 70 MiB on disk (about 33%).
  Final regular-file payload: 73,537,869 bytes; 93 native files, all arm64.
- Two independent clean source-directory builds passed signing, payload audits
  and relocated Cocoa probes, with matching file inventories. Logs are generated
  at `build/repeat-1.log` and `build/repeat-2.log` by the repeat-build script.
- Runtime probes loaded 24 frames, 11 clips and 9 speech categories, constructed
  Settings and About, initialized the native login service without registration,
  and confirmed frozen Python prefixes and resources stayed inside the app.
- Bundled startup, duplicate launch prevention, SIGTERM shutdown and relaunch
  passed without stderr. All 156 existing regression tests and 5 new payload
  audit regression tests passed.
- No external non-system Mach-O load paths, checkout paths in compressed Python,
  development source files or saved user state were found. Eight native files
  still contain recognized vendor source/default-prefix strings. The strict
  absolute-build-path gate remains open; functional reproducibility passed.
- Intel, macOS 13, separate-account and Finder/Spotlight acceptance remain
  unverified for this candidate. No release tag, notarization or publication.
