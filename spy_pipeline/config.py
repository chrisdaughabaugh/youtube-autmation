import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the spy_pipeline directory
_BASE = Path(__file__).parent
load_dotenv(_BASE / ".env")


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(
            f"Missing required env var: {key}\n"
            f"Copy spy_pipeline/.env.template to spy_pipeline/.env and fill it in."
        )
    return val


# API keys
GROQ_API_KEY = _require("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# TTS
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-ChristopherNeural")

# Video
VIDEO_WIDTH = int(os.getenv("VIDEO_WIDTH", "1080"))
VIDEO_HEIGHT = int(os.getenv("VIDEO_HEIGHT", "1920"))
VIDEO_FPS = int(os.getenv("VIDEO_FPS", "30"))
TARGET_DURATION_MIN = int(os.getenv("TARGET_DURATION_MIN", "60"))
TARGET_DURATION_MAX = int(os.getenv("TARGET_DURATION_MAX", "90"))

# Captions
CAPTION_FONT_SIZE = int(os.getenv("CAPTION_FONT_SIZE", "72"))
CAPTION_COLOR = os.getenv("CAPTION_COLOR", "#FFFFFF")

# Paths (resolved relative to this file)
MUSIC_PATH = _BASE / os.getenv("MUSIC_PATH", "assets/music")
FONTS_PATH = _BASE / "assets/fonts"
OUTPUT_PATH = _BASE / "output"
TOPICS_PATH = _BASE / "topics.txt"

# Batch
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
