"""Create and verify the release ZIP after building Nomzy.app on macOS."""
import hashlib
import platform
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path


def package(app: Path) -> Path:
    app = app.resolve()
    metadata = plistlib.loads((app / "Contents/Info.plist").read_bytes())
    version = metadata["CFBundleShortVersionString"]
    archive = app.parent / f"Nomzy-{version}-macOS-{platform.machine()}.zip"
    subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                    str(app), str(archive)], check=True)
    with tempfile.TemporaryDirectory(prefix="nomzy-install-") as directory:
        root = Path(directory)
        subprocess.run(["ditto", "-x", "-k", str(archive), str(root / "Downloads")], check=True)
        # Exercise a copy into an Applications directory, then app replacement.
        # This is deliberately isolated from the user's installed app and data.
        installed = root / "Applications/Nomzy.app"
        for attempt in range(2):
            if attempt:
                installed.rename(root / "Previous Nomzy.app")
            subprocess.run(["ditto", str(root / "Downloads/Nomzy.app"), str(installed)], check=True)
        subprocess.run([sys.executable, str(Path(__file__).with_name("verify_bundle.py")),
                        str(installed)], check=True)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{checksum}  {archive.name}\n")
    print(f"Verified release archive: {archive}")
    return archive


if __name__ == "__main__":
    package(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/Nomzy.app"))
