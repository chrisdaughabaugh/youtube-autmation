import json
import random
import sys
import textwrap
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_audioclips,
    concatenate_videoclips,
)
from moviepy.audio.fx import MultiplyVolume

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

W = config.VIDEO_WIDTH
H = config.VIDEO_HEIGHT


def _scene_duration(caption: str | None, narration: str = "") -> float:
    """Pace each scene so captions are comfortably readable."""
    text = caption or narration
    words = len(text.split()) if text else 0
    # ~120 wpm comfortable reading pace + 2s buffer for the visual to register
    return max(4.0, min(9.0, words * 0.5 + 2.5))


def _pick_music() -> Path | None:
    music_dir = config.MUSIC_PATH
    if not music_dir.exists():
        return None
    tracks = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
    if not tracks:
        print("  WARNING: No music files in assets/music — proceeding without music.")
        return None
    return random.choice(tracks)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        config.FONTS_PATH / "DejaVuSans-Bold.ttf",
        config.FONTS_PATH / "FreeSansBold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def _caption_image(text: str) -> np.ndarray:
    fs = config.CAPTION_FONT_SIZE
    wrapped = textwrap.fill(text.upper(), width=16)
    font = _load_font(fs)

    dummy = Image.new("RGBA", (1, 1))
    bbox = ImageDraw.Draw(dummy).textbbox((0, 0), wrapped, font=font)
    tw = bbox[2] - bbox[0] + 60
    th = bbox[3] - bbox[1] + 60

    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Heavy outline for contrast on any background
    for dx in range(-4, 5):
        for dy in range(-4, 5):
            if dx != 0 or dy != 0:
                d.text((30 + dx, 30 + dy), wrapped, font=font, fill=(0, 0, 0, 230))
    d.text((30, 30), wrapped, font=font, fill=(255, 255, 255, 255))

    return np.array(img)


def _make_scene_clip(frame_path: Path, duration: float, caption: str | None) -> CompositeVideoClip:
    img_arr = np.array(Image.open(frame_path).convert("RGB"))

    def zoom_frame(t):
        scale = 1.0 + 0.05 * (t / max(duration, 0.01))
        h, w = img_arr.shape[:2]
        nh, nw = int(h * scale), int(w * scale)
        resized = np.array(Image.fromarray(img_arr).resize((nw, nh), Image.LANCZOS))
        y0 = (nh - h) // 2
        x0 = (nw - w) // 2
        return resized[y0:y0 + h, x0:x0 + w]

    base = ImageClip(zoom_frame, duration=duration, ismask=False)
    layers = [base]

    if caption:
        cap_arr = _caption_image(caption)
        cap_h, cap_w = cap_arr.shape[:2]
        cap_x = (W - cap_w) // 2
        cap_y = int(H * 0.70)
        cap_clip = (
            ImageClip(cap_arr, duration=duration - 0.15, is_mask=False)
            .with_position((cap_x, cap_y))
            .with_start(0.15)
        )
        layers.append(cap_clip)

    return CompositeVideoClip(layers, size=(W, H)).with_duration(duration)


def assemble_video(story: dict, frame_paths: list[Path], out_dir: Path) -> Path:
    scenes = story["scenes"]

    # Build segment list: hook + scenes + payoff
    segments = [{"label": "hook", "caption": None, "narration": story["hook"]}]
    for i, scene in enumerate(scenes):
        segments.append({
            "label": f"scene_{i:02d}",
            "caption": scene.get("caption"),
            "narration": scene.get("narration", ""),
        })
    segments.append({"label": "payoff", "caption": story["payoff"].upper(), "narration": story["payoff"]})

    # Assign durations
    for seg in segments:
        seg["duration"] = _scene_duration(seg["caption"], seg["narration"])

    total = sum(s["duration"] for s in segments)
    print(f"  Timing: {len(segments)} segments, {total:.1f}s total")

    # Save timing for reference
    (out_dir / "timing.json").write_text(json.dumps({"segments": segments, "total": total}, indent=2))

    # Build video clips
    clips = []
    for i, seg in enumerate(segments):
        frame = frame_paths[i] if i < len(frame_paths) else frame_paths[-1]
        clips.append(_make_scene_clip(frame, seg["duration"], seg["caption"]))

    video = concatenate_videoclips(clips, method="compose")

    # Music — full-ish volume since there's no voice to compete with
    music_path = _pick_music()
    if music_path:
        music = AudioFileClip(str(music_path))
        if music.duration < video.duration:
            loops = int(video.duration / music.duration) + 1
            music = concatenate_audioclips([music] * loops)
        music = music.subclipped(0, video.duration).with_effects([MultiplyVolume(0.35)])
        video = video.with_audio(music)
        print(f"  Music: {music_path.name}")
    else:
        print("  No music — exporting silent video.")

    out_path = out_dir / "video.mp4"
    video.write_videofile(
        str(out_path),
        fps=config.VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        ffmpeg_params=["-crf", "23"],
        logger=None,
    )
    print(f"  Video saved -> {out_path}")
    return out_path
