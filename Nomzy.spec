# Build on macOS with: python -m PyInstaller Nomzy.spec
from pathlib import Path

root = Path(SPECPATH)
version = {}
exec((root / "src/nomzy/__init__.py").read_text(), version)
a = Analysis(
    [str(root / "packaging/launcher.py")],
    pathex=[str(root / "src")],
    datas=[(str(root / "assets"), "assets"), (str(root / "config/settings.json"), "config"),
           (str(root / "config/speech.json"), "config")],
    hiddenimports=["AppKit", "Foundation", "ServiceManagement"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Nomzy", console=False)
collection = COLLECT(exe, a.binaries, a.datas, name="Nomzy")
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
