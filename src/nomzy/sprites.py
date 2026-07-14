import json
from dataclasses import dataclass

from PySide6.QtGui import QPixmap

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

    sheet_path = get_assets_dir() / str(manifest["sheet"])
    if not sheet_path.exists():
        raise FileNotFoundError(f"Missing sprite sheet: {sheet_path}")

    sheet = QPixmap(str(sheet_path))
    if sheet.isNull():
        raise RuntimeError(f"Could not load sprite sheet: {sheet_path}")

    columns = max(1, int(manifest["grid"]["columns"]))
    rows = max(1, int(manifest["grid"]["rows"]))
    frames = _slice_sprite_sheet(sheet, columns, rows)
    clips = _load_clips(manifest["clips"], len(frames))
    anchor = manifest.get("anchor", {})

    return SpriteAssets(
        frames=tuple(frames),
        clips=clips,
        anchor_x=float(anchor.get("x", 0.5)),
        anchor_y=float(anchor.get("y", 1.0)),
    )


def _slice_sprite_sheet(sheet: QPixmap, columns: int, rows: int) -> list[QPixmap]:
    frames = []

    for row in range(rows):
        top = round(row * sheet.height() / rows)
        bottom = round((row + 1) * sheet.height() / rows)

        for column in range(columns):
            left = round(column * sheet.width() / columns)
            right = round((column + 1) * sheet.width() / columns)
            frames.append(sheet.copy(left, top, right - left, bottom - top))

    return frames


def _load_clips(raw_clips: dict, frame_count: int) -> dict[str, AnimationClip]:
    clips = {}

    for name, raw_clip in raw_clips.items():
        frames = tuple(
            AnimationFrame(
                sprite=int(raw_frame["sprite"]),
                duration_ms=max(1, int(raw_frame["duration_ms"])),
            )
            for raw_frame in raw_clip["frames"]
        )

        if not frames:
            raise ValueError(f"Animation '{name}' has no frames")

        if any(frame.sprite < 0 or frame.sprite >= frame_count for frame in frames):
            raise ValueError(f"Animation '{name}' references an invalid sprite")

        clips[name] = AnimationClip(
            name=name,
            frames=frames,
            loop=bool(raw_clip.get("loop", True)),
        )

    required_clips = {
        "idle",
        "blink",
        "walk",
        "talk",
        "pet",
        "treat",
        "ball",
        "paused",
    }
    missing_clips = required_clips - clips.keys()
    if missing_clips:
        missing = ", ".join(sorted(missing_clips))
        raise ValueError(f"Animation manifest is missing clips: {missing}")

    return clips
