# Build on macOS with: python -m PyInstaller Nomzy.spec
from pathlib import Path
import platform
import sysconfig

root = Path(SPECPATH)
version = {}
exec((root / "src/nomzy/__init__.py").read_text(), version)
a = Analysis(
    [str(root / "packaging/launcher.py")],
    pathex=[str(root / "src")],
    datas=[(str(root / "assets/nomzy_animations.json"), "assets"),
           *[(str(path), "assets/animations") for path in sorted((root / "assets/animations").glob("*.png"))],
           (str(root / "config/settings.json"), "config"),
           (str(root / "config/speech.json"), "config")],
    hiddenimports=["AppKit", "Foundation", "ServiceManagement"],
    hookspath=[str(root / "packaging/hooks")],
    # No network/TLS features. Avoid unused OpenSSL libraries and their
    # build-environment certificate/module search paths. hashlib retains its
    # standard-library fallback implementations.
    excludes=["_ssl", "_hashlib", sysconfig._get_sysconfigdata_name()],
)
# Nomzy has no translated UI. Filter before collection/signing, never mutate a
# finished app. Native Cocoa styles and platform plugins remain hook-managed.
a.datas = [entry for entry in a.datas if "/translations/" not in entry[0]]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Nomzy", console=False,
          target_arch=platform.machine())
collection = COLLECT(exe, a.binaries, a.datas, name="Nomzy", strip=True)
app = BUNDLE(
    collection,
    name="Nomzy.app",
    icon=str(root / "packaging/Nomzy.icns"),
    bundle_identifier="com.nomzy.desktop-companion",
    version=version["__version__"],
    info_plist={
        "CFBundleName": "Nomzy",
        "CFBundleDisplayName": "Nomzy",
        "NSHumanReadableCopyright": "Copyright © 2026 Nomzy contributors.",
        "LSUIElement": True,
        "LSMinimumSystemVersion": "13.0",
        "CFBundleShortVersionString": version["__version__"],
        "CFBundleVersion": version["__version__"],
        "NSHighResolutionCapable": True,
    },
)
