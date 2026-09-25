"""Reject release dependency drift before packaging."""
from importlib.metadata import version
from pathlib import Path
import platform
import sys

assert sys.platform == "darwin" and sys.version_info[:2] == (3, 11)
assert platform.machine() in {"arm64", "x86_64"}
requirements = Path(__file__).resolve().parents[1] / "packaging/requirements-build.txt"
for line in requirements.read_text().splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    name, expected = line.split("==")
    actual = version(name)
    assert actual == expected, f"{name}: expected {expected}, installed {actual}"
print(f"Release toolchain verified: Python {platform.python_version()}, {platform.machine()}")
