"""Build and verify twice in independent source directories using one toolchain.

This checks functional reproducibility and matching payload inventories, not
byte-identical signed executables. The existing dist directory is untouched.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
inventories = []
with tempfile.TemporaryDirectory(prefix="nomzy-repeat-") as temporary:
    for attempt in (1, 2):
        checkout = Path(temporary) / str(attempt)
        checkout.mkdir()
        for name in ("src", "assets", "config", "packaging", "scripts"):
            shutil.copytree(root / name, checkout / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(root / "Nomzy.spec", checkout / "Nomzy.spec")
        environment = dict(os.environ, PYTHON=sys.executable)
        log = root / "build" / f"repeat-{attempt}.log"
        log.parent.mkdir(exist_ok=True)
        with log.open("w") as output:
            result = subprocess.run(["sh", "scripts/build_macos.sh"], cwd=checkout,
                                    env=environment, stdout=output, stderr=subprocess.STDOUT)
        if result.returncode:
            raise SystemExit(f"Build {attempt} failed; see {log}")
        app = checkout / "dist/Nomzy.app"
        inventories.append(sorted(str(p.relative_to(app)) for p in app.rglob("*")))
        print(f"Build {attempt}: relocated runtime and payload audit passed; {log}", flush=True)
    assert inventories[0] == inventories[1], "Bundle inventories differ between clean builds"
print("PASS: two independent clean builds; matching inventories; both relocated apps work")
