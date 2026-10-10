import unittest
from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from nomzy.about_window import AboutWindow
from nomzy.activity import CompanionEvent
from nomzy.companion import NomzyDog
from nomzy.settings import DEFAULT_SETTINGS


class BetaRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        party_day = patch('nomzy.rendering.is_party_day', return_value=False)
        party_day.start()
        self.addCleanup(party_day.stop)
        with patch('nomzy.companion.load_settings', return_value=dict(DEFAULT_SETTINGS)):
            self.dog = NomzyDog()
        for timer in self.dog.findChildren(QTimer):
            timer.stop()
        self.addCleanup(self.dog.deleteLater)
        self.dog.settings.update(movement_enabled=False, speech_enabled=False)
        self.dog.scheduler.blink_cooldown_ms = self.dog.scheduler.rest_cooldown_ms = 3600000

    def test_stable_paused_sprite_does_not_request_repaints(self):
        self.dog.transition_activity(CompanionEvent.PAUSE)
        self.dog.tick()
        with patch.object(self.dog, 'update') as update, patch.object(self.dog, 'update_overlay_mask') as mask:
            for _ in range(100):
                self.dog.tick()
        update.assert_not_called()
        mask.assert_not_called()
        self.assertFalse(hasattr(self.dog, 'mask_timer'))

    def test_frame_direction_and_day_changes_request_repaints(self):
        self.dog.tick()
        self.dog.last_direction *= -1
        with patch.object(self.dog, 'update') as update:
            self.dog.tick()
            update.assert_called_once()
        with patch('nomzy.rendering.is_party_day', return_value=True), patch.object(self.dog, 'update') as update:
            self.dog.tick()
            update.assert_called_once()
        self.dog.start_reaction('pet')
        self.dog.update_animation(0)
        self.dog.tick()
        self.dog.animation_player.advance(500)
        with patch.object(self.dog, 'update') as update:
            self.dog.tick()
            update.assert_called_once()

    def test_unchanged_mask_is_not_reset_but_cleared_mask_is_restored(self):
        self.dog.update_overlay_mask()
        original = self.dog.mask()
        self.assertFalse(original.isEmpty())
        with patch.object(self.dog, 'setMask', wraps=self.dog.setMask) as setter:
            self.dog.update_overlay_mask()
            setter.assert_not_called()
            self.dog.clearMask()
            self.dog.update_overlay_mask()
            setter.assert_called_once()
        self.assertEqual(self.dog.mask(), original)

    def test_speech_expiry_repaints_and_removes_bubble_mask_while_paused(self):
        self.dog.transition_activity(CompanionEvent.PAUSE)
        self.dog.say_message('Hello, friend!')
        self.dog.tick()
        bubble_mask = self.dog.mask()
        self.dog.scheduler.message_ticks_remaining = 1
        with patch.object(self.dog, 'update') as update:
            self.dog.tick()
            update.assert_called_once()
        self.assertEqual(self.dog.message, '')
        self.assertNotEqual(self.dog.mask(), bubble_mask)
        self.assertTrue(self.dog.activity.paused)

    def test_about_exposes_support_links_and_log_location(self):
        window = AboutWindow(self.dog.get_scaled_sprite())
        self.addCleanup(window.deleteLater)
        self.assertIn('/issues', window.support_label.text())
        self.assertIn('~/Library/Logs/Nomzy/nomzy.log', window.support_label.text())
        self.assertTrue(window.support_label.openExternalLinks())
