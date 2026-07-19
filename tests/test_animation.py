import unittest

from nomzy.animation import (
    AnimationClip,
    AnimationFrame,
    AnimationPlayback,
    AnimationPlayer,
)


class AnimationPlayerTests(unittest.TestCase):
    def setUp(self):
        self.clips = {
            "loop": AnimationClip(
                name="loop",
                frames=(
                    AnimationFrame(sprite=0, duration_ms=100),
                    AnimationFrame(sprite=1, duration_ms=200),
                ),
                playback=AnimationPlayback.LOOP,
            ),
            "once": AnimationClip(
                name="once",
                frames=(
                    AnimationFrame(sprite=2, duration_ms=50),
                    AnimationFrame(sprite=3, duration_ms=75),
                ),
                playback=AnimationPlayback.RETURN,
            ),
            "hold": AnimationClip(
                name="hold",
                frames=(
                    AnimationFrame(sprite=4, duration_ms=50),
                    AnimationFrame(sprite=5, duration_ms=75),
                    AnimationFrame(sprite=6, duration_ms=25),
                ),
                playback=AnimationPlayback.HOLD,
                hold_frame=1,
            ),
        }

    def test_looping_clip_uses_elapsed_time(self):
        player = AnimationPlayer(self.clips, "loop")

        player.advance(99)
        self.assertEqual(player.frame.sprite, 0)

        player.advance(1)
        self.assertEqual(player.frame.sprite, 1)

        player.advance(200)
        self.assertEqual(player.frame.sprite, 0)
        self.assertFalse(player.finished)

    def test_one_shot_holds_its_final_frame(self):
        player = AnimationPlayer(self.clips, "loop")
        player.play("once")
        player.advance(125)

        self.assertEqual(player.frame.sprite, 3)
        self.assertTrue(player.finished)

        player.advance(500)
        self.assertEqual(player.frame.sprite, 3)

    def test_play_does_not_restart_the_active_clip_unless_requested(self):
        player = AnimationPlayer(self.clips, "loop")
        player.advance(100)
        player.play("loop")
        self.assertEqual(player.frame.sprite, 1)

        player.play("loop", restart=True)
        self.assertEqual(player.frame.sprite, 0)

    def test_hold_clip_settles_on_its_configured_frame(self):
        player = AnimationPlayer(self.clips, "loop")
        player.play("hold")
        player.advance(150)

        self.assertTrue(player.finished)
        self.assertEqual(player.frame.sprite, 5)


if __name__ == "__main__":
    unittest.main()
