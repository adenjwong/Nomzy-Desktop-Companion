import json
from dataclasses import dataclass

from PySide6.QtGui import QPixmap, QRegion

from .animation import AnimationClip, AnimationFrame
from .paths import get_animation_manifest_path, get_assets_dir


@dataclass(frozen=True)
class SpriteAssets:
    frames: tuple[QPixmap, ...]
    clips: dict[str, AnimationClip]
    anchor_x: float
    anchor_y: float


def load_sprite_assets() -> SpriteAssets:
    manifest_path = get_animation_manifest_path()

    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing animation manifest: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as file:
        manifest = json.load(file)

    frames, source_frames = _load_sources(manifest["sources"])
    clips = _load_clips(manifest["clips"], source_frames)
    anchor = manifest.get("anchor", {})

    return SpriteAssets(
        frames=tuple(frames),
        clips=clips,
        anchor_x=float(anchor.get("x", 0.5)),
        anchor_y=float(anchor.get("y", 1.0)),
    )


def _load_sources(
    raw_sources: dict,
) -> tuple[list[QPixmap], dict[str, tuple[int, ...]]]:
    if not raw_sources:
        raise ValueError("Animation manifest has no sources")

    frames = []
    source_frames = {}

    for source_name, raw_source in raw_sources.items():
        source_path = get_assets_dir() / str(raw_source["file"])
        if not source_path.exists():
            raise FileNotFoundError(f"Missing animation source: {source_path}")

        source = QPixmap(str(source_path))
        if source.isNull():
            raise RuntimeError(f"Could not load animation source: {source_path}")

        grid = raw_source["grid"]
        columns = max(1, int(grid["columns"]))
        rows = max(1, int(grid["rows"]))
        source_indices = []

        for frame in _slice_grid(source, columns, rows):
            source_indices.append(len(frames))
            frames.append(_trim_transparent_frame(frame, source_name))

        source_frames[source_name] = tuple(source_indices)

    return frames, source_frames


def _slice_grid(source: QPixmap, columns: int, rows: int) -> list[QPixmap]:
    frames = []

    for row in range(rows):
        top = round(row * source.height() / rows)
        bottom = round((row + 1) * source.height() / rows)

        for column in range(columns):
            left = round(column * source.width() / columns)
            right = round((column + 1) * source.width() / columns)
            frames.append(source.copy(left, top, right - left, bottom - top))

    return frames


def _trim_transparent_frame(frame: QPixmap, source_name: str) -> QPixmap:
    if not frame.hasAlphaChannel():
        return frame

    visible_rect = QRegion(frame.mask()).boundingRect()
    if visible_rect.isEmpty():
        raise ValueError(f"Animation source '{source_name}' has an empty frame")

    return frame.copy(visible_rect)


def _load_clips(
    raw_clips: dict,
    source_frames: dict[str, tuple[int, ...]],
) -> dict[str, AnimationClip]:
    clips = {}

    for name, raw_clip in raw_clips.items():
        frames = []

        for raw_frame in raw_clip["frames"]:
            source_name = str(raw_frame["source"])
            if source_name not in source_frames:
                raise ValueError(
                    f"Animation '{name}' references unknown source '{source_name}'"
                )

            source_sprite = int(raw_frame["sprite"])
            if source_sprite < 0 or source_sprite >= len(source_frames[source_name]):
                raise ValueError(
                    f"Animation '{name}' references an invalid sprite in "
                    f"source '{source_name}'"
                )

            frames.append(
                AnimationFrame(
                    sprite=source_frames[source_name][source_sprite],
                    duration_ms=max(1, int(raw_frame["duration_ms"])),
                )
            )

        frames = tuple(frames)

        if not frames:
            raise ValueError(f"Animation '{name}' has no frames")

        clips[name] = AnimationClip(
            name=name,
            frames=frames,
            loop=bool(raw_clip.get("loop", True)),
            render_scale=max(0.1, float(raw_clip.get("render_scale", 1.0))),
        )

    required_clips = {
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
    missing_clips = required_clips - clips.keys()
    if missing_clips:
        missing = ", ".join(sorted(missing_clips))
        raise ValueError(f"Animation manifest is missing clips: {missing}")

    return clips
