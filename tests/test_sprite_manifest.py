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

        self.assertFalse(talk["loop"])
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

            self.assertFalse(clip["loop"])
            self.assertEqual(
                (start["source"], start["sprite"]),
                (end["source"], end["sprite"]),
            )

    def test_drag_animation_settles_on_the_open_hanging_pose(self):
        drag = self.manifest["clips"]["drag"]

        self.assertFalse(drag["loop"])
        self.assertEqual(drag["render_scale"], 1.2)
        self.assertEqual(
            (drag["frames"][-1]["source"], drag["frames"][-1]["sprite"]),
            ("drag", 3),
        )


if __name__ == "__main__":
    unittest.main()
