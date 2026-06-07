"""
generate_voiceover.py — StoicElderWisdom
Deep, warm, unhurried voice for men 45–65.
Priority: Kokoro (local) -> Google Cloud TTS -> Edge TTS
"""
import asyncio
import base64
import json
import os
import re
import subprocess
import sys
import numpy as np
import requests
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


def load_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    env = Path(".env")
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


def generate_google_tts(text: str, mp3_path: Path) -> bool:
    """Use Google Cloud TTS via the REST API — same key as Gemini (if billing enabled)."""
    api_key = load_api_key()
    if not api_key:
        return False
    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
    payload = {
        "input": {"text": text[:5000]},
        "voice": {
            "languageCode": "en-US",
            "name": "en-US-Neural2-D",   # deep, warm male voice
            "ssmlGender": "MALE",
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": 0.85,
            "pitch": -3.0,
        },
    }
    try:
        print("  Google Cloud TTS: en-US-Neural2-D (deep male, 0.85x speed)")
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 403:
            print("  Google TTS: billing not enabled on this API key — skipping")
            return False
        resp.raise_for_status()
        audio_b64 = resp.json().get("audioContent", "")
        if not audio_b64:
            return False
        mp3_path.write_bytes(base64.b64decode(audio_b64))

        # Script > 5000 chars needs chunking — handle remaining chunks
        remaining = text[5000:]
        if remaining:
            chunks = [remaining[i:i+5000] for i in range(0, len(remaining), 5000)]
            parts = [mp3_path.read_bytes()]
            for chunk in chunks:
                payload["input"]["text"] = chunk
                r = requests.post(url, json=payload, timeout=60)
                r.raise_for_status()
                parts.append(base64.b64decode(r.json().get("audioContent", "")))
            mp3_path.write_bytes(b"".join(parts))

        print(f"  MP3 saved: {mp3_path}")
        return True
    except Exception as e:
        print(f"  Google TTS failed: {e}")
        return False


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
    elif generate_google_tts(script, mp3_path):
        pass
    else:
        print("  Falling back to Edge TTS...")
        asyncio.run(generate_edge(script, mp3_path))

    print(f"\nDone: {mp3_path}")


if __name__ == "__main__":
    main()
