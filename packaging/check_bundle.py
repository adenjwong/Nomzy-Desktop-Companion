"""Read-only frozen-runtime probe, invoked by scripts/verify_bundle.py."""
import json
import platform
import sys
import traceback
from pathlib import Path


def verify(report_path):
    try:
        import AppKit
        import Foundation
        import ServiceManagement
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QImageReader
        from nomzy.login_item import LoginItem
        from nomzy.settings_window import NomzySettingsWindow
        from nomzy.about_window import AboutWindow
        from nomzy import __version__
        from nomzy.paths import (APPLICATION_NAME, ORGANIZATION_NAME, get_assets_dir,
                                 get_bundled_config_dir, get_settings_path, get_state_path)
        from nomzy.sprites import _load_sprite_assets
        from nomzy.speech import load_speech

        app = QApplication(["Nomzy bundle verification"])
        app.setApplicationName(APPLICATION_NAME)
        app.setOrganizationName(ORGANIZATION_NAME)
        assert getattr(sys, "frozen", False), "Probe must run in the packaged app"
        bundle = Path(sys.executable).resolve().parents[1]
        assert Path(sys.prefix).resolve().is_relative_to(bundle), sys.prefix
        assert Path(sys.base_prefix).resolve().is_relative_to(bundle), sys.base_prefix
        for path in (get_assets_dir(), get_bundled_config_dir()):
            assert path.resolve().is_relative_to(bundle), f"External resource: {path}"
        for path in (get_settings_path(), get_state_path()):
            assert not path.resolve().is_relative_to(bundle), f"Data inside bundle: {path}"
        # Use the strict loader: fallback artwork must not conceal missing assets.
        sprites = _load_sprite_assets()
        assert sprites.frames and all(not frame.isNull() for frame in sprites.frames)
        config = get_bundled_config_dir()
        defaults = json.loads((config / "settings.json").read_text())
        speech = json.loads((config / "speech.json").read_text())
        assert defaults and speech
        loaded_speech = load_speech()
        assert all(loaded_speech[key] == value for key, value in speech.items())
        assert hasattr(ServiceManagement, "SMAppService")
        assert LoginItem().service is not None, "Native login service unavailable"
        assert b"png" in QImageReader.supportedImageFormats()
        # Construct auxiliary windows to exercise their frozen imports/resources.
        settings_window = NomzySettingsWindow(defaults, lambda settings: None)
        about_window = AboutWindow(sprites.frames[0])
        settings_window.close()
        about_window.close()
        report = {"ok": True, "version": __version__, "frames": len(sprites.frames),
                  "architecture": platform.machine(), "qt_platform": app.platformName(),
                  "clips": len(sprites.clips), "speech_categories": len(speech),
                  "settings_path": str(get_settings_path()),
                  "resource_root": str(get_assets_dir().parent),
                  "python": sys.version, "native_bridges": True}
    except Exception:
        report = {"ok": False, "error": traceback.format_exc()}
    Path(report_path).write_text(json.dumps(report, indent=2) + "\n")
    return 0 if report["ok"] else 1
