"""
generate_short.py
Creates a 55-second vertical (1080x1920) YouTube Short from the opening
of the voiceover. Trims audio + subtitles, then renders a mobile-optimised
vertical video to tease the full video.
Output: output/short.mp4
"""
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR     = Path("output")
VOICEOVER      = OUTPUT_DIR / "voiceover.mp3"
SUBTITLES      = OUTPUT_DIR / "subtitles.srt"
SHORT_AUDIO    = OUTPUT_DIR / "short_audio.mp3"
SHORT_SRT      = OUTPUT_DIR / "short.srt"
SHORT_OUT      = OUTPUT_DIR / "short.mp4"

SHORT_DURATION = 55   # seconds — keeps it under YouTube's 60s Short limit
FPS            = 24

# Prefer close-up images — they fill the vertical frame best
BG_CANDIDATES = [
    "generated_images/03_close_up_determined_bw.jpg",
    "generated_images/06_close_up_eyes_fire_reflection.jpg",
    "generated_images/15_close_up_final_calm_absolute.jpg",
    "generated_images/08_bust_shadow_half_light_bw.jpg",
]


def pick_bg() -> Path:
    for p in BG_CANDIDATES:
        path = Path(p)
        if path.exists():
            return path
    images = sorted(Path("generated_images").glob("*.jpg"))
    if images:
        return images[0]
    raise FileNotFoundError("No background images found in generated_images/")


def trim_audio() -> None:
    print(f"Trimming audio to {SHORT_DURATION}s...")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(VOICEOVER),
        "-t", str(SHORT_DURATION),
        "-c", "copy",
        str(SHORT_AUDIO),
    ], check=True, capture_output=True)
    print(f"  Saved: {SHORT_AUDIO}")


def trim_srt() -> None:
    """Keep only subtitle blocks that start before SHORT_DURATION."""
    print("Trimming subtitles...")

    def ts_to_sec(ts: str) -> float:
        h, m, s = ts.strip().replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    content = SUBTITLES.read_text(encoding="utf-8")
    blocks  = [b.strip() for b in content.strip().split("\n\n") if b.strip()]

    kept, idx = [], 1
    for block in blocks:
        lines   = block.split("\n")
        ts_line = next((l for l in lines if "-->" in l), None)
        if not ts_line:
            continue
        if ts_to_sec(ts_line.split("-->")[0]) >= SHORT_DURATION:
            break
        text_lines = [l for l in lines if "-->" not in l and not l.strip().isdigit()]
        kept.append(f"{idx}\n{ts_line}\n" + "\n".join(text_lines))
        idx += 1

    SHORT_SRT.write_text("\n\n".join(kept) + "\n", encoding="utf-8")
    print(f"  {len(kept)} subtitle cards -> {SHORT_SRT}")


def build_short() -> None:
    bg = pick_bg()
    print(f"Building vertical Short from: {bg}")

    srt_escaped = str(SHORT_SRT.resolve()).replace("\\", "/").replace(":", "\\:")
    d = SHORT_DURATION * FPS  # total frames for zoompan

    vf = (
        # Scale landscape image to fill 1080x1920, center-crop to vertical
        f"scale=1920:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        # Slow zoom-in Ken Burns effect
        f"zoompan=z='1.0+0.04*on/{d}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={d}:s=1080x1920:fps={FPS},"
        # Subtitles — larger font for mobile vertical viewing
        f"subtitles='{srt_escaped}'"
        f":force_style='FontName=Arial,FontSize=28,Bold=1,"
        f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        f"Outline=4,Alignment=2,MarginV=120'"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(bg),
        "-i", str(SHORT_AUDIO),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", str(SHORT_DURATION),
        "-shortest",
        "-movflags", "+faststart",
        str(SHORT_OUT),
    ], check=True)
    print(f"\nDone: {SHORT_OUT}")


def main() -> None:
    if not VOICEOVER.exists():
        print(f"ERROR: {VOICEOVER} not found. Run generate_voiceover.py first.")
        sys.exit(1)
    if not SUBTITLES.exists():
        print(f"ERROR: {SUBTITLES} not found. Run generate_subtitles.py first.")
        sys.exit(1)

    trim_audio()
    trim_srt()
    build_short()
    print("Short ready: output/short.mp4")


if __name__ == "__main__":
    main()
