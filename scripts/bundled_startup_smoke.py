"""Check duplicate launch, SIGTERM, and relaunch without changing login settings."""
import subprocess
import sys
import tempfile
import time
from pathlib import Path

app_path = (Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else
            Path(__file__).resolve().parents[1] / "dist/Nomzy.app")
binary = app_path / "Contents/MacOS/Nomzy"


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            raise AssertionError("Nomzy did not exit within 10 seconds")


with tempfile.TemporaryDirectory() as directory:
    for attempt in range(2):
        process = subprocess.Popen([str(binary)], cwd=directory,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            time.sleep(3)
            if attempt == 0 and process.poll() == 0:
                raise SystemExit("SKIPPED: Nomzy is already running; quit it before this check.")
            assert process.poll() is None, "Nomzy exited during startup"
            duplicate = subprocess.run([str(binary)], cwd=directory,
                                       capture_output=True, timeout=10)
            assert duplicate.returncode == 0, "Duplicate launch failed"
            assert not duplicate.stderr, duplicate.stderr.decode(errors="replace")
        finally:
            stop(process)
        stdout, stderr = process.communicate()
        assert process.returncode == 0, f"Unclean shutdown: {process.returncode}"
        assert not stderr, stderr.decode(errors="replace")
    print("PASS: bundled startup, duplicate launch, SIGTERM shutdown, relaunch; no stderr")
