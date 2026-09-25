"""Release gate regressions: contaminated payloads must fail before launch."""
import marshal
from pathlib import Path
import tempfile
import unittest

from scripts.verify_bundle import audit_bundle, check_paths


class BundleAuditTests(unittest.TestCase):
    def test_rejects_checkout_paths_in_compiled_python(self):
        code = compile("answer = 42", "/Users/builder/project/src/main.py", "exec")
        with self.assertRaisesRegex(AssertionError, "Development path"):
            check_paths(marshal.dumps(code), "nomzy.main")

    def test_vendor_exception_does_not_hide_application_paths(self):
        with self.assertRaisesRegex(AssertionError, "Development path"):
            check_paths(b"/Users/qt/work/private/settings.json", "nomzy.settings")

    def test_vendor_diagnostics_are_reported(self):
        self.assertTrue(check_paths(b"/Users/qt/work/qt/source.cpp\0",
                                    "Contents/Frameworks/QtWidgets"))
        self.assertFalse(check_paths(b"@rpath/QtWidgets\0", "Contents/Frameworks/QtWidgets"))

    def test_rejects_shipped_user_state(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory)
            (app / "state.json").write_text("{}")
            with self.assertRaisesRegex(AssertionError, "Development/user file"):
                audit_bundle(app)

    def test_rejects_external_resource_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "Nomzy.app"
            app.mkdir()
            external = root / "asset.png"
            external.write_bytes(b"artwork")
            (app / "asset.png").symlink_to(external)
            with self.assertRaisesRegex(AssertionError, "Invalid symlink"):
                audit_bundle(app)
