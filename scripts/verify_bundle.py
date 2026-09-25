"""Verify a relocated app with no Python, Qt, or repository environment variables."""
import argparse
import json
import marshal
import os
import platform
import plistlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


def check_paths(content, label):
    # These are vendor build provenance/diagnostics, not runtime lookup paths.
    # Keep the exceptions narrow; every Mach-O load command is checked separately.
    original = content
    if str(label).startswith("Contents/Frameworks/"):
        content = re.sub(rb"/Users/qt/work/[^\x00\s]+", b"<qt-source>", content)
        content = re.sub(rb"/Users/runner/miniforge3/conda-bld/[^\x00\s]+", b"<conda-source>", content)
    if str(label).endswith("/libpython3.11.dylib"):
        # CPython's compiled default prefix; the frozen bootloader overrides it.
        content = re.sub(rb"\x00/opt/anaconda3/envs/[^/\x00]+\x00", b"\x00<python-build-prefix>\x00", content)
    assert not re.search(rb"/(?:Users|home)/[^/\x00\s]+/|/opt/(?:homebrew|anaconda3)/|/private/var/folders/", content), f"Development path: {label}"
    return content != original


def audit_python(app_path):
    from PyInstaller.archive.readers import CArchiveReader

    archive = CArchiveReader(str(app_path / "Contents/MacOS/Nomzy"))
    for name, entry in archive.toc.items():
        if entry[-1] == "z":
            modules = archive.open_embedded_archive(name)
            for module in modules.toc:
                check_paths(marshal.dumps(modules.extract(module)), module)
        elif entry[-1] in {"s", "m", "M"}:
            check_paths(archive.extract(name), name)
    with zipfile.ZipFile(app_path / "Contents/Resources/base_library.zip") as library:
        for name in library.namelist():
            check_paths(library.read(name), name)


def audit_bundle(app_path):
    """Check the actual payload, including each native library and load command."""
    forbidden = {".git", ".venv", ".venv-build", "tests", "__pycache__",
                 ".DS_Store", "state.json", ".pytest_cache", "Headers"}
    native_count = 0
    vendor_path_files = []
    payload_bytes = 0
    magic = {b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe",
             b"\xfe\xed\xfa\xcf", b"\xbe\xba\xfe\xca"}
    for path in sorted(app_path.rglob("*")):
        relative = path.relative_to(app_path)
        assert not forbidden.intersection(relative.parts), f"Development/user file: {relative}"
        assert path.suffix not in {".h", ".py", ".a", ".pro"}, f"Development file: {relative}"
        if path.is_symlink():
            assert path.exists() and path.resolve().is_relative_to(app_path), f"Invalid symlink: {relative}"
            continue
        if not path.is_file():
            continue
        content = path.read_bytes()
        payload_bytes += len(content)
        if check_paths(content, relative):
            vendor_path_files.append(str(relative))
        if content[:4] not in magic:
            continue
        native_count += 1
        architectures = subprocess.check_output(["lipo", "-archs", str(path)], text=True).split()
        assert architectures == [platform.machine()], (relative, architectures)
        commands = subprocess.check_output(["otool", "-l", str(path)], text=True)
        for line in commands.splitlines():
            match = re.match(r"\s*(?:name|path) (.+) \(offset \d+\)", line)
            if match:
                dependency = match[1]
                assert not dependency.startswith("/") or dependency.startswith(("/System/Library/", "/usr/lib/")), (relative, dependency)
    assert native_count, "No native payload found"
    audit_python(app_path)
    return {"architecture": platform.machine(), "native_files": native_count,
            "payload_bytes": payload_bytes,
            "vendor_build_path_files": vendor_path_files,
            "zero_absolute_build_paths": not vendor_path_files}


def verify(app_path, strict_build_paths=False):
    audit = audit_bundle(app_path)
    if strict_build_paths:
        assert audit["zero_absolute_build_paths"], audit["vendor_build_path_files"]
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
        assert data["architecture"] == audit["architecture"]
        assert data["qt_platform"] == "cocoa"
        data["audit"] = audit
        print(json.dumps(data, indent=2))
        print("PASS: signed bundle structure, relocated runtime, artwork, speech, native bridges, external user data")
        if not audit["zero_absolute_build_paths"]:
            print("PENDING: zero absolute build paths; vendor diagnostics/default Python prefix remain")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", nargs="?", default="dist/Nomzy.app")
    parser.add_argument("--strict-build-paths", action="store_true")
    arguments = parser.parse_args()
    verify(Path(arguments.app).resolve(), arguments.strict_build_paths)
