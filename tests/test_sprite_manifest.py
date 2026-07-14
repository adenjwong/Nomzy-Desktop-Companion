import json
import unittest
from pathlib import Path


class SpriteManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repo_root = Path(__file__).resolve().parents[1]
        manifest_path = repo_root / "assets" / "nomzy_animations.json"
        cls.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cls.sheet_path = repo_root / "assets" / cls.manifest["sheet"]

    def test_manifest_references_an_existing_sheet(self):
        self.assertTrue(self.sheet_path.exists())

    def test_required_clips_are_present(self):
        required = {
            "idle",
            "blink",
            "walk",
            "talk",
            "pet",
            "treat",
            "ball",
            "paused",
        }
        self.assertTrue(required.issubset(self.manifest["clips"]))

    def test_frame_references_fit_the_grid(self):
        grid = self.manifest["grid"]
        frame_count = grid["columns"] * grid["rows"]

        for clip in self.manifest["clips"].values():
            self.assertTrue(clip["frames"])
            for frame in clip["frames"]:
                self.assertIn(frame["sprite"], range(frame_count))
                self.assertGreater(frame["duration_ms"], 0)

    def test_talking_gestures_three_times_then_returns_to_neutral(self):
        talk = self.manifest["clips"]["talk"]
        expression_frames = [
            frame for frame in talk["frames"] if frame["sprite"] != 0
        ]

        self.assertFalse(talk["loop"])
        self.assertEqual(len(expression_frames), 3)
        self.assertEqual(talk["frames"][-1]["sprite"], 0)


if __name__ == "__main__":
    unittest.main()
