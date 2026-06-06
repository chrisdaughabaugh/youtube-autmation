"""
assemble_video.py — FFmpeg-based video assembly (fast)
Combines images + voiceover into a 1080p MP4 with Ken Burns zoom effect.
If generated_clips/ contains .mp4 files, uses those instead of static images.
"""
import subprocess
import sys
import json
from pathlib import Path

IMAGES_DIR  = Path("generated_images")
CLIPS_DIR   = Path("generated_clips")
AUDIO_PATH  = Path("output") / "voiceover.mp3"
OUTPUT_PATH = Path("output") / "video_raw.mp4"
OUTPUT_DIR  = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

W, H = 1920, 1080
FPS  = 24


def get_audio_duration(audio_path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", str(audio_path)],
        capture_output=True, text=True, check=True
    )
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


# Cap how long a single image stays on screen — keeps viewer attention (pattern break)
MAX_SECONDS_PER_IMAGE = 16


def build_filter(image_files: list, duration_each: float) -> tuple[list, str]:
    """Build FFmpeg input args and zoompan/concat filter string.
    Caps per-image duration at MAX_SECONDS_PER_IMAGE, looping images if needed.
    Uses 4 Ken Burns motions for visual variety: zoom-in, zoom-out, pan-left, pan-right.
    """
    # If images would show too long, tile them to create more cuts
    actual_dur = min(duration_each, MAX_SECONDS_PER_IMAGE)
    if duration_each > MAX_SECONDS_PER_IMAGE:
        # Repeat image list until we fill the total audio duration
        total_dur   = duration_each * len(image_files)
        repeats     = int(total_dur / actual_dur) + 1
        image_files = (image_files * repeats)[:repeats]

    inputs       = []
    filter_parts = []
    zoom_frames  = int(actual_dur * FPS)

    # 4-motion cycle: zoom-in centre, pan-left, zoom-out centre, pan-right
    MOTIONS = [
        # (zoom_expr, x_expr, y_expr)
        (f"'1.0+0.06*on/{zoom_frames}'", "iw/2-(iw/zoom/2)",           "ih/2-(ih/zoom/2)"),    # zoom in
        (f"'1.06'",                       f"iw*0.04*on/{zoom_frames}",   "ih/2-(ih/zoom/2)"),    # pan left→right
        (f"'1.06-0.06*on/{zoom_frames}'", "iw/2-(iw/zoom/2)",           "ih/2-(ih/zoom/2)"),    # zoom out
        (f"'1.06'",                       f"iw*0.04*(1-on/{zoom_frames})","ih/2-(ih/zoom/2)"),   # pan right→left
    ]

    for i, img in enumerate(image_files):
        inputs += ["-loop", "1", "-t", str(actual_dur + 0.1), "-i", str(img)]
        zoom_expr, x_expr, y_expr = MOTIONS[i % 4]
        zp = (
            f"[{i}:v]scale={W*2}:{H*2},"
            f"zoompan=z={zoom_expr}:x={x_expr}:y={y_expr}"
            f":d={zoom_frames}:s={W}x{H}:fps={FPS},"
            f"trim=duration={actual_dur},setpts=PTS-STARTPTS[v{i}]"
        )
        filter_parts.append(zp)

    concat_inputs = "".join(f"[v{i}]" for i in range(len(image_files)))
    concat = f"{concat_inputs}concat=n={len(image_files)}:v=1:a=0[vout]"
    filter_parts.append(concat)

    return inputs, ";".join(filter_parts)


def assemble_from_clips(clip_files: list) -> None:
    """Concatenate animated video clips with audio overlay."""
    if not AUDIO_PATH.exists():
        print(f"Audio not found: {AUDIO_PATH}")
        sys.exit(1)

    # Write concat list file
    concat_list = OUTPUT_DIR / "clips_concat.txt"
    concat_list.write_text("\n".join(f"file '{c.resolve()}'" for c in clip_files))

    # Concatenate clips silently, then mux with voiceover
    silent_concat = OUTPUT_DIR / "clips_silent.mp4"
    concat_cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-an", str(silent_concat),
    ]
    print("Concatenating animated clips...")
    subprocess.run(concat_cmd, check=True, capture_output=False)

    mux_cmd = [
        "ffmpeg", "-y",
        "-i", str(silent_concat),
        "-i", str(AUDIO_PATH),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(OUTPUT_PATH),
    ]
    print("Muxing audio...")
    result = subprocess.run(mux_cmd, capture_output=False)
    silent_concat.unlink(missing_ok=True)
    concat_list.unlink(missing_ok=True)

    if result.returncode == 0:
        print(f"\nDone (animated clips): {OUTPUT_PATH}")
    else:
        print(f"\nFFmpeg mux failed — falling back to static images")
        assemble_from_images()


def assemble_from_images() -> None:
    """Original static image assembly with Ken Burns effect."""
    image_files = sorted(IMAGES_DIR.glob("*.jpg")) + sorted(IMAGES_DIR.glob("*.png"))
    if not image_files:
        print(f"No images found in {IMAGES_DIR}/")
        sys.exit(1)

    print("Getting audio duration...")
    total_dur = get_audio_duration(AUDIO_PATH)
    n         = len(image_files)
    dur_each  = total_dur / n
    capped    = min(dur_each, MAX_SECONDS_PER_IMAGE)
    print(f"Audio: {total_dur:.1f}s | {n} images | {dur_each:.1f}s each -> capped at {capped:.1f}s")

    print("Building FFmpeg filter...")
    img_inputs, vf = build_filter(image_files, dur_each)

    n_audio = len(img_inputs) // 6

    cmd = [
        "ffmpeg", "-y",
        *img_inputs,
        "-i", str(AUDIO_PATH),
        "-filter_complex", vf,
        "-map", "[vout]",
        "-map", f"{n_audio}:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(OUTPUT_PATH),
    ]

    print(f"Rendering -> {OUTPUT_PATH}")
    print("This will take 2-5 minutes...")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode == 0:
        print(f"\nDone (static images): {OUTPUT_PATH}")
    else:
        print(f"\nFFmpeg failed with code {result.returncode}")
        sys.exit(1)


def main():
    if not AUDIO_PATH.exists():
        print(f"Audio not found: {AUDIO_PATH}")
        sys.exit(1)

    clip_files = sorted(CLIPS_DIR.glob("*.mp4")) if CLIPS_DIR.exists() else []

    if clip_files:
        print(f"Found {len(clip_files)} animated clips — using Veo animation mode")
        assemble_from_clips(clip_files)
    else:
        print("No animated clips found — using static image mode (Ken Burns)")
        assemble_from_images()


if __name__ == "__main__":
    main()
