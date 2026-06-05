import json
import os
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
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.audio.fx import MultiplyVolume

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

W = config.VIDEO_WIDTH
H = config.VIDEO_HEIGHT


def _pick_music() -> Path | None:
    music_dir = config.MUSIC_PATH
    if not music_dir.exists():
        return None
    tracks = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
    if not tracks:
        print("  WARNING: No music files found in assets/music. Proceeding without music.")
        return None
    return random.choice(tracks)


def _caption_image(text: str, width: int, font_size: int = None) -> np.ndarray:
    fs = font_size or config.CAPTION_FONT_SIZE
    wrapped = textwrap.fill(text.upper(), width=18)

    font = None
    for font_name in ["DejaVuSans-Bold.ttf", "FreeSansBold.ttf", "LiberationSans-Bold.ttf"]:
        font_path = config.FONTS_PATH / font_name
        if font_path.exists():
            font = ImageFont.truetype(str(font_path), fs)
            break
    if font is None:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", fs)
        except Exception:
            font = ImageFont.load_default()

    # Measure text
    dummy = Image.new("RGBA", (1, 1))
    dd = ImageDraw.Draw(dummy)
    bbox = dd.textbbox((0, 0), wrapped, font=font)
    tw = bbox[2] - bbox[0] + 40
    th = bbox[3] - bbox[1] + 40

    img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Shadow / outline
    for dx in [-3, -2, 0, 2, 3]:
        for dy in [-3, -2, 0, 2, 3]:
            if dx != 0 or dy != 0:
                d.text((20 + dx, 20 + dy), wrapped, font=font, fill=(0, 0, 0, 220))
    d.text((20, 20), wrapped, font=font, fill=(255, 255, 255, 255))

    return np.array(img)


def _make_scene_clip(frame_path: Path, duration: float, caption: str | None,
                     scene_idx: int) -> CompositeVideoClip:
    img_arr = np.array(Image.open(frame_path).convert("RGB"))

    # Slow zoom: scale from 1.0 to 1.06 over the clip's duration
    def zoom_frame(t):
        scale = 1.0 + 0.06 * (t / max(duration, 0.01))
        h, w = img_arr.shape[:2]
        new_h = int(h * scale)
        new_w = int(w * scale)
        resized = np.array(Image.fromarray(img_arr).resize((new_w, new_h), Image.LANCZOS))
        y0 = (new_h - h) // 2
        x0 = (new_w - w) // 2
        return resized[y0:y0 + h, x0:x0 + w]

    base = ImageClip(zoom_frame, duration=duration, ismask=False)
    layers = [base]

    if caption:
        cap_arr = _caption_image(caption)
        cap_clip = ImageClip(cap_arr, duration=duration, is_mask=False)

        # Pop-in at 0.15s, fade out at end
        cap_clip = cap_clip.with_effects([])
        cap_w = cap_arr.shape[1]
        cap_h = cap_arr.shape[0]
        cap_x = (W - cap_w) // 2
        cap_y = int(H * 0.72)

        cap_clip = cap_clip.with_position((cap_x, cap_y))
        cap_clip = cap_clip.with_start(0.15)

        layers.append(cap_clip)

    clip = CompositeVideoClip(layers, size=(W, H))
    clip = clip.with_duration(duration)
    return clip


def assemble_video(story: dict, segments: list[dict], frame_paths: list[Path],
                   out_dir: Path) -> Path:
    timing_path = out_dir / "timing.json"
    timing = json.loads(timing_path.read_text())

    clips = []
    for i, seg in enumerate(timing["segments"]):
        frame = frame_paths[i] if i < len(frame_paths) else frame_paths[-1]
        caption = seg.get("caption")
        clip = _make_scene_clip(frame, seg["duration"], caption, i)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")

    # Narration audio
    narration = AudioFileClip(timing["narration_path"])
    audio_tracks = [narration]

    # Background music (ducked)
    music_path = _pick_music()
    if music_path:
        music = AudioFileClip(str(music_path))
        total = video.duration
        if music.duration < total:
            # loop
            loops = int(total / music.duration) + 1
            from moviepy import concatenate_audioclips
            music = concatenate_audioclips([music] * loops)
        music = music.subclipped(0, total)
        music = music.with_effects([MultiplyVolume(0.12)])
        audio_tracks.append(music)
        print(f"  Music track: {music_path.name}")

    composite_audio = CompositeAudioClip(audio_tracks)
    video = video.with_audio(composite_audio)

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
