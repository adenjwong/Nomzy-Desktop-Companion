import json
from dataclasses import dataclass

from PySide6.QtGui import QPixmap, QRegion

from .activity import CompanionState
from .animation import AnimationClip, AnimationFrame, AnimationPlayback
from .paths import get_animation_manifest_path, get_assets_dir


@dataclass(frozen=True)
class SpriteAssets:
    frames: tuple[QPixmap, ...]
    clips: dict[str, AnimationClip]
    activity_clips: dict[CompanionState, str]
    anchor_x: float
    anchor_y: float


def load_sprite_assets() -> SpriteAssets:
    manifest_path = get_animation_manifest_path()

    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing animation manifest: {manifest_path}")

    with open(manifest_path, "r", encoding="utf-8") as file:
        manifest = json.load(file)

    if not isinstance(manifest, dict):
        raise ValueError("Animation manifest must contain an object")
    if manifest.get("schema_version") != 1:
        raise ValueError("Animation manifest has an unsupported schema version")

    frames, source_frames = _load_sources(manifest["sources"])
    clips = _load_clips(
        manifest["clips"],
        source_frames,
        manifest.get("defaults", {}),
    )
    activity_clips = _load_activity_clips(manifest["activities"], clips)
    anchor = manifest.get("anchor", {})

    return SpriteAssets(
        frames=tuple(frames),
        clips=clips,
        activity_clips=activity_clips,
        anchor_x=float(anchor.get("x", 0.5)),
        anchor_y=float(anchor.get("y", 1.0)),
    )


def _load_sources(
    raw_sources: dict,
) -> tuple[list[QPixmap], dict[str, tuple[int, ...]]]:
    if not isinstance(raw_sources, dict) or not raw_sources:
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
        columns = int(grid["columns"])
        rows = int(grid["rows"])
        if columns <= 0 or rows <= 0:
            raise ValueError(
                f"Animation source '{source_name}' has an invalid grid"
            )
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
    defaults: dict,
) -> dict[str, AnimationClip]:
    if not isinstance(raw_clips, dict) or not raw_clips:
        raise ValueError("Animation manifest has no clips")
    if not isinstance(defaults, dict):
        raise ValueError("Animation manifest has invalid defaults")

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

            duration_ms = int(raw_frame["duration_ms"])
            if duration_ms <= 0:
                raise ValueError(
                    f"Animation '{name}' has an invalid frame duration"
                )

            frames.append(
                AnimationFrame(
                    sprite=source_frames[source_name][source_sprite],
                    duration_ms=duration_ms,
                )
            )

        frames = tuple(frames)

        if not frames:
            raise ValueError(f"Animation '{name}' has no frames")

        try:
            playback = AnimationPlayback(str(raw_clip["playback"]))
        except KeyError as error:
            raise ValueError(
                f"Animation '{name}' has no playback behavior"
            ) from error
        except ValueError as error:
            raise ValueError(
                f"Animation '{name}' has invalid playback behavior"
            ) from error

        hold_frame = raw_clip.get("hold_frame")
        if playback is AnimationPlayback.HOLD and hold_frame is None:
            raise ValueError(f"Animation '{name}' has no hold frame")
        if playback is not AnimationPlayback.HOLD and hold_frame is not None:
            raise ValueError(
                f"Animation '{name}' only needs a hold frame when playback holds"
            )
        if hold_frame is not None:
            hold_frame = int(hold_frame)
            if hold_frame < 0 or hold_frame >= len(frames):
                raise ValueError(f"Animation '{name}' has an invalid hold frame")

        render_scale = float(
            raw_clip.get(
                "render_scale",
                defaults.get("render_scale", 1.0),
            )
        )
        if render_scale <= 0:
            raise ValueError(f"Animation '{name}' has an invalid render scale")

        mirror_with_direction = raw_clip.get(
            "mirror_with_direction",
            defaults.get("mirror_with_direction", True),
        )
        if not isinstance(mirror_with_direction, bool):
            raise ValueError(
                f"Animation '{name}' has an invalid mirroring setting"
            )

        clips[name] = AnimationClip(
            name=name,
            frames=frames,
            playback=playback,
            hold_frame=hold_frame,
            render_scale=render_scale,
            mirror_with_direction=mirror_with_direction,
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


def _load_activity_clips(
    raw_activities: dict,
    clips: dict[str, AnimationClip],
) -> dict[CompanionState, str]:
    if not isinstance(raw_activities, dict):
        raise ValueError("Animation manifest has invalid activities")

    activity_clips = {}
    required_states = set(CompanionState) - {CompanionState.REACTING}
    required_names = {state.name.lower() for state in required_states}
    unknown_names = set(raw_activities) - required_names
    if unknown_names:
        unknown = ", ".join(sorted(unknown_names))
        raise ValueError(f"Animation manifest has unknown activities: {unknown}")

    for state in required_states:
        activity_name = state.name.lower()
        clip_name = raw_activities.get(activity_name)
        if not isinstance(clip_name, str) or clip_name not in clips:
            raise ValueError(
                f"Activity '{activity_name}' does not reference a valid clip"
            )
        activity_clips[state] = clip_name

    return activity_clips
