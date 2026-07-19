import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication, QRegion

from nomzy.activity import CompanionState
from nomzy.animation import AnimationPlayback
from nomzy.sprites import (
    _load_activity_clips,
    _load_clips,
    load_sprite_assets,
)


class SpriteLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])
        cls.assets = load_sprite_assets()

    def test_all_source_frames_load(self):
        self.assertEqual(len(self.assets.frames), 24)
        self.assertTrue(all(not frame.isNull() for frame in self.assets.frames))

    def test_frames_are_trimmed_to_visible_pixels(self):
        for frame in self.assets.frames:
            self.assertEqual(QRegion(frame.mask()).boundingRect(), frame.rect())

    def test_rest_clips_are_available(self):
        self.assertIn("sit", self.assets.clips)
        self.assertIn("sleep", self.assets.clips)

    def test_sitting_blink_preserves_the_seated_sprite_size(self):
        sit_clip = self.assets.clips["sit"]
        open_frame = self.assets.frames[sit_clip.frames[3].sprite]
        blink_frame = self.assets.frames[sit_clip.frames[4].sprite]

        self.assertEqual(blink_frame.size(), open_frame.size())

    def test_drag_clip_is_available(self):
        self.assertIn("drag", self.assets.clips)
        self.assertEqual(self.assets.clips["drag"].render_scale, 1.2)

    def test_playback_behavior_loads_from_the_manifest(self):
        self.assertEqual(
            self.assets.clips["idle"].playback,
            AnimationPlayback.LOOP,
        )
        self.assertEqual(
            self.assets.clips["sit"].playback,
            AnimationPlayback.RETURN,
        )
        self.assertEqual(
            self.assets.clips["drag"].playback,
            AnimationPlayback.HOLD,
        )
        self.assertEqual(self.assets.clips["drag"].hold_frame, 3)

    def test_activity_clip_mapping_loads_from_the_manifest(self):
        self.assertEqual(self.assets.activity_clips[CompanionState.IDLE], "idle")
        self.assertEqual(
            self.assets.activity_clips[CompanionState.WALKING],
            "walk",
        )
        self.assertEqual(
            self.assets.activity_clips[CompanionState.MENU],
            "paused",
        )

    def test_clip_without_playback_behavior_is_rejected(self):
        raw_clips = {
            "idle": {
                "frames": [
                    {"source": "idle", "sprite": 0, "duration_ms": 100}
                ]
            }
        }

        with self.assertRaisesRegex(ValueError, "no playback behavior"):
            _load_clips(raw_clips, {"idle": (0,)}, {})

    def test_hold_clip_without_hold_frame_is_rejected(self):
        raw_clips = {
            "idle": {
                "playback": "hold",
                "frames": [
                    {"source": "idle", "sprite": 0, "duration_ms": 100}
                ],
            }
        }

        with self.assertRaisesRegex(ValueError, "no hold frame"):
            _load_clips(raw_clips, {"idle": (0,)}, {})

    def test_unknown_activity_name_is_rejected(self):
        activities = {
            state.name.lower(): "idle"
            for state in CompanionState
            if state is not CompanionState.REACTING
        }
        activities["flying"] = "idle"

        with self.assertRaisesRegex(ValueError, "unknown activities: flying"):
            _load_activity_clips(activities, self.assets.clips)


if __name__ == "__main__":
    unittest.main()
