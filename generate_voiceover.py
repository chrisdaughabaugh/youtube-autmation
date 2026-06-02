"""
generate_voiceover.py — StoicElderWisdom
Deep, warm, unhurried voice for men 45–65.
Kokoro primary (am_michael), Edge TTS fallback (ChristopherNeural at -15% rate).
"""
import asyncio
import re
import subprocess
import sys
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

VOICE = "am_michael"
SPEED = 0.82   # unhurried — this audience hates being rushed

# Edge TTS fallback — warm, measured, mature
EDGE_VOICE  = "en-US-ChristopherNeural"
EDGE_RATE   = "-15%"
EDGE_PITCH  = "-10Hz"

SCRIPT = """
Most men your age are carrying something they've never spoken out loud.
Peace doesn't come from fixing the past. It comes from releasing it.
"""


def clean_script(text: str) -> str:
    """Strip markup that TTS would read aloud literally."""
    # **bold** → word (remove asterisks, keep text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    # *italic* → word
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    # // pause markers → comma pause
    text = text.replace('//', ',')
    # Remove any remaining lone asterisks
    text = text.replace('*', '')
    # Collapse multiple commas / spaces
    text = re.sub(r',\s*,+', ',', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def generate_kokoro(text: str, wav_path: Path) -> bool:
    try:
        from kokoro import KPipeline
    except ImportError:
        try:
            print("  Installing Kokoro...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "kokoro>=0.9.4", "soundfile", "misaki[en]"],
                check=True, capture_output=True
            )
            from kokoro import KPipeline
        except Exception as e:
            print(f"  Kokoro install failed: {e}")
            return False

    try:
        import soundfile as sf
        print(f"  Kokoro: voice={VOICE}, speed={SPEED}")
        pipeline = KPipeline(lang_code="a")
        chunks   = [audio for _, _, audio in pipeline(text, voice=VOICE, speed=SPEED)]
        sf.write(str(wav_path), np.concatenate(chunks), 24000)
        print(f"  WAV saved: {wav_path}")
        return True
    except Exception as e:
        print(f"  Kokoro generation failed: {e}")
        return False


def wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    subprocess.run([
        "ffmpeg", "-y", "-i", str(wav_path),
        "-codec:a", "libmp3lame", "-b:a", "128k",
        str(mp3_path),
    ], check=True, capture_output=True)
    wav_path.unlink(missing_ok=True)
    print(f"  MP3 saved: {mp3_path}")


async def generate_edge(text: str, mp3_path: Path) -> None:
    import edge_tts
    print(f"  Edge TTS: voice={EDGE_VOICE}, rate={EDGE_RATE}, pitch={EDGE_PITCH}")
    comm = edge_tts.Communicate(text.strip(), EDGE_VOICE, rate=EDGE_RATE, pitch=EDGE_PITCH)
    await comm.save(str(mp3_path))
    print(f"  MP3 saved: {mp3_path}")


def main():
    script_file = OUTPUT_DIR / "script.txt"
    script = script_file.read_text(encoding="utf-8") if script_file.exists() else SCRIPT
    if script_file.exists():
        print("Loaded script from output/script.txt")

    mp3_path = OUTPUT_DIR / "voiceover.mp3"
    wav_path = OUTPUT_DIR / "voiceover.wav"

    script = clean_script(script)
    print("Generating voiceover...")

    if generate_kokoro(script, wav_path):
        wav_to_mp3(wav_path, mp3_path)
    else:
        print("  Falling back to Edge TTS...")
        asyncio.run(generate_edge(script, mp3_path))

    print(f"\nDone: {mp3_path}")


if __name__ == "__main__":
    main()
