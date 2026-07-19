import json
import unittest
from pathlib import Path


class SpriteManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo_root = Path(__file__).resolve().parents[1]
        manifest_path = repo_root / "assets" / "nomzy_animations.json"
        cls.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cls.assets_dir = repo_root / "assets"

    def test_manifest_references_the_upgraded_animation_sources(self):
        expected_files = {
            "animations/nomzy_idle_blink_strip.png",
            "animations/nomzy_walk_strip.png",
            "animations/nomzy_eye_scrunch_strip.png",
            "animations/nomzy_sit_strip.png",
            "animations/nomzy_sit_blink.png",
            "animations/nomzy_sleepy_lie_down_strip.png",
            "animations/nomzy_scruff_drag_strip.png",
        }
        source_files = {
            source["file"] for source in self.manifest["sources"].values()
        }

        self.assertEqual(source_files, expected_files)
        for source_file in source_files:
            self.assertTrue((self.assets_dir / source_file).exists())

    def test_required_clips_are_present(self):
        required = {
            "idle",
            "blink",
            "walk",
            "talk",
            "pet",
            "treat",
            "ball",
            "sit",
            "sleep",
            "drag",
            "paused",
        }
        self.assertTrue(required.issubset(self.manifest["clips"]))

    def test_manifest_declares_its_schema_and_playback_defaults(self):
        self.assertEqual(self.manifest["schema_version"], 1)
        self.assertEqual(self.manifest["defaults"]["render_scale"], 1.0)
        self.assertTrue(
            self.manifest["defaults"]["mirror_with_direction"]
        )

        valid_playback = {"loop", "return", "hold"}
        for clip in self.manifest["clips"].values():
            self.assertIn(clip["playback"], valid_playback)

    def test_every_activity_references_a_clip(self):
        expected_activities = {
            "idle",
            "walking",
            "blinking",
            "sitting",
            "sleeping",
            "talking",
            "dragging",
            "paused",
            "menu",
        }

        self.assertEqual(set(self.manifest["activities"]), expected_activities)
        for clip_name in self.manifest["activities"].values():
            self.assertIn(clip_name, self.manifest["clips"])

    def test_frame_references_fit_the_grid(self):
        for clip in self.manifest["clips"].values():
            self.assertTrue(clip["frames"])
            for frame in clip["frames"]:
                self.assertIn(frame["source"], self.manifest["sources"])
                grid = self.manifest["sources"][frame["source"]]["grid"]
                frame_count = grid["columns"] * grid["rows"]
                self.assertIn(frame["sprite"], range(frame_count))
                self.assertGreater(frame["duration_ms"], 0)

    def test_every_animation_source_is_used(self):
        used_sources = {
            frame["source"]
            for clip in self.manifest["clips"].values()
            for frame in clip["frames"]
        }

        self.assertEqual(used_sources, set(self.manifest["sources"]))

    def test_talking_gestures_once_then_returns_to_neutral(self):
        talk = self.manifest["clips"]["talk"]
        neutral_frame = {"source": "idle", "sprite": 0}
        expression_frames = [
            frame
            for frame in talk["frames"]
            if {
                "source": frame["source"],
                "sprite": frame["sprite"],
            }
            != neutral_frame
        ]

        self.assertEqual(talk["playback"], "hold")
        self.assertEqual(talk["hold_frame"], len(talk["frames"]) - 1)
        self.assertEqual(len(expression_frames), 1)
        self.assertEqual(
            {
                "source": talk["frames"][-1]["source"],
                "sprite": talk["frames"][-1]["sprite"],
            },
            neutral_frame,
        )

    def test_rest_animations_return_to_standing(self):
        for clip_name in ("sit", "sleep"):
            clip = self.manifest["clips"][clip_name]
            start = clip["frames"][0]
            end = clip["frames"][-1]

            self.assertEqual(clip["playback"], "return")
            self.assertEqual(
                (start["source"], start["sprite"]),
                (end["source"], end["sprite"]),
            )

    def test_rest_animations_hold_their_resting_poses(self):
        sit_frames = self.manifest["clips"]["sit"]["frames"]
        sleep_frames = self.manifest["clips"]["sleep"]["frames"]

        seated_frames = [
            frame
            for frame in sit_frames
            if frame["source"] == "sit_blink"
            or (frame["source"], frame["sprite"]) == ("sit", 3)
        ]

        self.assertEqual(sum(frame["duration_ms"] for frame in seated_frames), 7000)
        self.assertEqual(sleep_frames[7]["duration_ms"], 11000)

    def test_sitting_animation_blinks_once_without_moving(self):
        sit_frames = self.manifest["clips"]["sit"]["frames"]
        blink_indices = [
            index
            for index, frame in enumerate(sit_frames)
            if frame["source"] == "sit_blink"
        ]

        self.assertEqual(blink_indices, [4])
        blink_index = blink_indices[0]
        for adjacent_index in (blink_index - 1, blink_index + 1):
            adjacent = sit_frames[adjacent_index]
            self.assertEqual(
                (adjacent["source"], adjacent["sprite"]),
                ("sit", 3),
            )

    def test_drag_animation_settles_on_the_open_hanging_pose(self):
        drag = self.manifest["clips"]["drag"]

        self.assertEqual(drag["playback"], "hold")
        self.assertEqual(drag["hold_frame"], len(drag["frames"]) - 1)
        self.assertEqual(drag["render_scale"], 1.2)
        self.assertEqual(
            (drag["frames"][-1]["source"], drag["frames"][-1]["sprite"]),
            ("drag", 3),
        )


if __name__ == "__main__":
    unittest.main()
