"""Verify a relocated app with no Python, Qt, or repository environment variables."""
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def verify(app_path):
    with (app_path / "Contents/Info.plist").open("rb") as file:
        metadata = plistlib.load(file)
    assert metadata["CFBundleIdentifier"] == "com.nomzy.desktop-companion"
    assert metadata["CFBundleName"] == metadata["CFBundleDisplayName"] == "Nomzy"
    assert metadata["LSMinimumSystemVersion"] == "13.0"
    assert metadata["NSHumanReadableCopyright"]
    assert metadata["LSUIElement"] is True
    icon = app_path / "Contents/Resources" / metadata["CFBundleIconFile"]
    assert icon.read_bytes()[:4] == b"icns", "Missing application icon"
    assert not list(app_path.rglob("state.json")), "User state shipped in bundle"
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app_path)], check=True)
    with tempfile.TemporaryDirectory(prefix="nomzy-relocated-") as directory:
        root = Path(directory)
        relocated = root / "Nomzy.app"
        shutil.copytree(app_path, relocated, symlinks=True)
        report = root / "report.json"
        environment = {key: os.environ[key] for key in ("HOME", "TMPDIR", "USER", "LOGNAME")
                       if key in os.environ}
        environment["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
        result = subprocess.run([str(relocated / "Contents/MacOS/Nomzy"),
                                 "--verify-bundle", str(report)], cwd=root,
                                env=environment, capture_output=True, timeout=60)
        data = json.loads(report.read_text()) if report.exists() else {}
        assert result.returncode == 0 and data.get("ok"), (data, result.stderr.decode())
        assert data["version"] == metadata["CFBundleShortVersionString"] == metadata["CFBundleVersion"]
        print(json.dumps(data, indent=2))
        print("PASS: signed bundle structure, relocated runtime, artwork, speech, native bridges, external user data")


if __name__ == "__main__":
    verify(Path(sys.argv[1] if len(sys.argv) > 1 else "dist/Nomzy.app").resolve())
