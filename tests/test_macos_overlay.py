"""Native policy tests; actual Spaces visibility also needs a Cocoa session."""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from nomzy.macos_overlay import configure_macos_overlay_window, prepare_settings_window, raise_macos_overlay


class NativePolicyTests(unittest.TestCase):
    def setUp(self):
        self.appkit = SimpleNamespace(
            NSNormalWindowLevel=0, NSStatusWindowLevel=25,
            NSFloatingWindowLevel=3, NSScreenSaverWindowLevel=1000,
            NSWindowCollectionBehaviorCanJoinAllSpaces=1,
            NSWindowCollectionBehaviorMoveToActiveSpace=2,
            NSWindowCollectionBehaviorStationary=16,
            NSWindowCollectionBehaviorIgnoresCycle=64,
            NSWindowCollectionBehaviorFullScreenAuxiliary=256,
            NSWindowStyleMaskNonactivatingPanel=128,
            NSColor=Mock(),
        )
        self.window = Mock()
        self.window.windowNumber.return_value = 42
        self.window.styleMask.return_value = 0
        self.widget = SimpleNamespace()
        for patcher in (
            patch.dict(sys.modules, AppKit=self.appkit),
            patch('nomzy.macos_overlay.has_native_macos_windowing', return_value=True),
            patch('nomzy.macos_overlay.get_ns_window', return_value=self.window),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_overlay_joins_spaces_at_requested_level_without_reordering(self):
        configure_macos_overlay_window(self.widget)
        self.window.setLevel_.assert_called_once_with(25)
        self.window.setCollectionBehavior_.assert_called_once_with(1 | 16 | 64 | 256)
        self.window.orderFrontRegardless.assert_not_called()
        self.window.makeKeyAndOrderFront_.assert_not_called()

    def test_unchanged_configuration_is_cached_but_show_and_replacement_reapply(self):
        configure_macos_overlay_window(self.widget)
        configure_macos_overlay_window(self.widget)
        self.assertEqual(self.window.setLevel_.call_count, 1)
        configure_macos_overlay_window(self.widget, force=True)
        self.assertEqual(self.window.setLevel_.call_count, 2)
        self.window.windowNumber.return_value = 43
        configure_macos_overlay_window(self.widget)
        self.assertEqual(self.window.setLevel_.call_count, 3)

    def test_level_and_activation_changes_apply_in_both_directions(self):
        configure_macos_overlay_window(self.widget)
        self.window.styleMask.return_value = 128
        configure_macos_overlay_window(self.widget, 'normal', False)
        self.window.setLevel_.assert_called_with(0)
        self.window.setStyleMask_.assert_called_with(0)
        self.window.styleMask.return_value = 0
        configure_macos_overlay_window(self.widget, 'status', True)
        self.window.setLevel_.assert_called_with(25)
        self.window.setStyleMask_.assert_called_with(128)

    def test_failed_configuration_is_retried(self):
        self.window.setLevel_.side_effect = RuntimeError('not ready')
        with self.assertLogs('nomzy.macos_overlay', level='WARNING'):
            configure_macos_overlay_window(self.widget)
        self.window.setLevel_.side_effect = None
        configure_macos_overlay_window(self.widget)
        self.assertEqual(self.window.setLevel_.call_count, 2)

    def test_explicit_locate_orders_without_making_key(self):
        self.assertTrue(raise_macos_overlay(self.widget))
        self.window.orderFrontRegardless.assert_called_once_with()
        self.window.makeKeyAndOrderFront_.assert_not_called()

    def test_settings_moves_to_active_space_without_joining_all_spaces(self):
        prepare_settings_window(self.widget)
        self.window.setCollectionBehavior_.assert_called_once_with(2 | 256)
        self.window.setLevel_.assert_not_called()
        self.window.makeKeyAndOrderFront_.assert_not_called()
