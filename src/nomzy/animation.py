from dataclasses import dataclass


@dataclass(frozen=True)
class AnimationFrame:
    sprite: int
    duration_ms: int


@dataclass(frozen=True)
class AnimationClip:
    name: str
    frames: tuple[AnimationFrame, ...]
    loop: bool = True

    @property
    def duration_ms(self) -> int:
        return sum(frame.duration_ms for frame in self.frames)


class AnimationPlayer:
    """Advances named animation clips using elapsed wall-clock time."""

    def __init__(self, clips: dict[str, AnimationClip], initial_clip: str):
        if initial_clip not in clips:
            raise KeyError(f"Unknown initial animation: {initial_clip}")

        self.clips = clips
        self.clip_name = initial_clip
        self.frame_index = 0
        self.elapsed_in_frame_ms = 0
        self.finished = False

    @property
    def clip(self) -> AnimationClip:
        return self.clips[self.clip_name]

    @property
    def frame(self) -> AnimationFrame:
        return self.clip.frames[self.frame_index]

    def play(self, clip_name: str, restart: bool = False) -> None:
        if clip_name not in self.clips:
            raise KeyError(f"Unknown animation: {clip_name}")

        if clip_name == self.clip_name and not restart:
            return

        self.clip_name = clip_name
        self.frame_index = 0
        self.elapsed_in_frame_ms = 0
        self.finished = False

    def advance(self, elapsed_ms: int) -> None:
        if elapsed_ms <= 0 or self.finished:
            return

        self.elapsed_in_frame_ms += elapsed_ms

        while self.elapsed_in_frame_ms >= self.frame.duration_ms:
            self.elapsed_in_frame_ms -= self.frame.duration_ms

            if self.frame_index + 1 < len(self.clip.frames):
                self.frame_index += 1
                continue

            if self.clip.loop:
                self.frame_index = 0
            else:
                self.frame_index = len(self.clip.frames) - 1
                self.elapsed_in_frame_ms = 0
                self.finished = True
                break
