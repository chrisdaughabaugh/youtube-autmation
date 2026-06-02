"""
generate_subtitles.py
1. Transcribes voiceover with Whisper (word-level timestamps)
2. Groups words into 4-word subtitle cards
3. Writes an SRT file
4. Burns subtitles onto video using FFmpeg (fast, no font issues)
"""
import sys
import subprocess
from pathlib import Path

OUTPUT_DIR = Path("output")
AUDIO_PATH = OUTPUT_DIR / "voiceover.mp3"
VIDEO_IN   = OUTPUT_DIR / "video_raw.mp4"
VIDEO_OUT  = OUTPUT_DIR / "final_with_subs.mp4"
SRT_PATH   = OUTPUT_DIR / "subtitles.srt"

MAX_WORDS  = 4


# ─────────────────────────────────────────────────────────────────────────────
# 1. Transcribe with Whisper
# ─────────────────────────────────────────────────────────────────────────────
def transcribe(audio_path: Path) -> list[dict]:
    try:
        import whisper
    except ImportError:
        print("ERROR: whisper not installed. Run: pip install openai-whisper")
        sys.exit(1)

    print("Loading Whisper model (first run downloads ~140 MB)...")
    model = whisper.load_model("base")
    print(f"Transcribing: {audio_path}")
    result = model.transcribe(
        str(audio_path),
        word_timestamps=True,
        language="en",
    )

    words = []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            words.append({
                "word":  w["word"].strip(),
                "start": w["start"],
                "end":   w["end"],
            })
    print(f"  {len(words)} words transcribed.")
    return words


# ─────────────────────────────────────────────────────────────────────────────
# 2. Group into subtitle cards
# ─────────────────────────────────────────────────────────────────────────────
def group_into_cards(words: list[dict], max_words: int = MAX_WORDS) -> list[dict]:
    cards = []
    i = 0
    while i < len(words):
        chunk = words[i : i + max_words]
        cards.append({
            "text":  " ".join(w["word"] for w in chunk),
            "start": chunk[0]["start"],
            "end":   chunk[-1]["end"],
        })
        i += max_words
    return cards


# ─────────────────────────────────────────────────────────────────────────────
# 3. Write SRT
# ─────────────────────────────────────────────────────────────────────────────
def write_srt(cards: list[dict], path: Path) -> None:
    def fmt(t: float) -> str:
        h  = int(t // 3600)
        m  = int((t % 3600) // 60)
        s  = int(t % 60)
        ms = int((t % 1) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    with open(path, "w", encoding="utf-8") as f:
        for i, card in enumerate(cards, 1):
            f.write(f"{i}\n{fmt(card['start'])} --> {fmt(card['end'])}\n{card['text']}\n\n")
    print(f"SRT saved: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# 4. Burn with FFmpeg (uses built-in font renderer — no font install needed)
# ─────────────────────────────────────────────────────────────────────────────
def burn_subtitles(srt_path: Path, video_in: Path, video_out: Path) -> None:
    # Escape Windows path for FFmpeg subtitles filter
    srt_escaped = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_in),
        "-vf", (
            f"subtitles='{srt_escaped}'"
            f":force_style='FontName=Arial,FontSize=22,Bold=1,"
            f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            f"Outline=3,Alignment=2,MarginV=40'"
        ),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-c:a", "copy",
        str(video_out),
    ]

    print(f"Burning subtitles -> {video_out}")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print(f"\nDone: {video_out}")
    else:
        print(f"\nFFmpeg failed with code {result.returncode}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if not VIDEO_IN.exists():
        print(f"Video not found: {VIDEO_IN}\nRun assemble_video.py first.")
        sys.exit(1)
    if not AUDIO_PATH.exists():
        print(f"Audio not found: {AUDIO_PATH}")
        sys.exit(1)

    words = transcribe(AUDIO_PATH)
    cards = group_into_cards(words)
    write_srt(cards, SRT_PATH)
    burn_subtitles(SRT_PATH, VIDEO_IN, VIDEO_OUT)


if __name__ == "__main__":
    main()
