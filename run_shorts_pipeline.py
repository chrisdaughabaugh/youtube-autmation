"""
run_shorts_pipeline.py — StoicElderWisdom
Generates and uploads standalone YouTube Shorts for men 45–65.
Each Short: Gemini script → Edge TTS voiceover → image → subtitles → vertical video → upload.
Default: 1 short per run (called every 3 hours by scheduler).
Usage: python run_shorts_pipeline.py [--count N]
"""
import asyncio
import io
import json
import os
import re
import socket
import subprocess
import sys
import time
import threading
import numpy as np

# Force UTF-8 stdout so special characters don't crash on Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from pathlib import Path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ── config ──────────────────────────────────────────────────────────────────────
SHORT_DURATION = 55
FPS            = 24
EDGE_VOICE     = "en-US-ChristopherNeural"
EDGE_RATE      = "-15%"
EDGE_PITCH     = "-10Hz"
OUTPUT_DIR     = Path("output/shorts_tmp")
CLIENT_SECRETS = Path("client_secrets.json")
TOKEN_FILE     = Path("token.json")
TOPICS_FILE    = Path("posted_topics.json")
SCOPES         = ["https://www.googleapis.com/auth/youtube.force-ssl"]

import argparse as _ap
_parser = _ap.ArgumentParser(add_help=False)
_parser.add_argument("--count",  type=int,  default=1)
_parser.add_argument("--teaser", action="store_true",
                     help="Generate a teaser short that references today's main video")
_args, _ = _parser.parse_known_args()
NUM_SHORTS = _args.count
TEASER_MODE = _args.teaser

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── helpers ──────────────────────────────────────────────────────────────────────
def clean_script(text: str) -> str:
    """Strip markup that TTS would read aloud literally."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*',     r'\1', text)
    text = text.replace('//', ',')
    text = text.replace('*', '')
    text = re.sub(r',\s*,+', ',', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


# ── Telegram ─────────────────────────────────────────────────────────────────────
def _load_tg() -> tuple[str, str]:
    cfg = {}
    env = Path(".env")
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    token   = os.environ.get("TELEGRAM_BOT_TOKEN",  cfg.get("TELEGRAM_BOT_TOKEN",  ""))
    chat_id = os.environ.get("TELEGRAM_CHAT_ID",    cfg.get("TELEGRAM_CHAT_ID",    ""))
    return token, chat_id


def tg(text: str) -> None:
    token, chat_id = _load_tg()
    if not token or not chat_id:
        return
    def _send():
        try:
            import urllib.request
            url  = f"https://api.telegram.org/bot{token}/sendMessage"
            data = json.dumps({"chat_id": chat_id, "text": text,
                               "parse_mode": "HTML"}).encode()
            req  = urllib.request.Request(url, data=data,
                                          headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()


# ── Gemini ────────────────────────────────────────────────────────────────────────
def load_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    env = Path(".env")
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise ValueError("GEMINI_API_KEY not found")


MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]


def call_gemini(prompt: str, api_key: str, retries: int = 3) -> str:
    """Call Gemini with full retry resilience.
    - 503 (service down): wait 30s/60s/90s then move to next model
    - 429 (rate limit): wait 60s/120s/180s then move to next model
    - If ALL models fail on first pass: wait 10 min, do a full second pass
    """
    import requests as _req

    def _try_models() -> str | None:
        for model in MODELS:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/"
                f"models/{model}:generateContent?key={api_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.95, "maxOutputTokens": 8192},
            }
            for attempt in range(1, retries + 1):
                try:
                    resp = _req.post(url, json=payload, timeout=90)
                    if resp.status_code == 429:
                        wait = 60 * attempt          # 60s, 120s, 180s
                        print(f"  {model} rate limited, waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    if resp.status_code == 503:
                        wait = 30 * attempt          # 30s, 60s, 90s
                        print(f"  {model} unavailable (503), waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    resp.raise_for_status()
                    candidate = resp.json()["candidates"][0]
                    finish    = candidate.get("finishReason", "UNKNOWN")
                    text      = candidate["content"]["parts"][0]["text"]
                    if finish == "MAX_TOKENS":
                        print(f"  {model} hit token limit — trying next model...")
                        break
                    print(f"  Using model: {model}  (finishReason={finish})")
                    return text
                except Exception as e:
                    print(f"  {model} attempt {attempt} failed: {e}")
                    if attempt < retries:
                        time.sleep(10)
            print(f"  {model} exhausted, trying next...")
        return None

    result = _try_models()
    if result:
        return result

    # All models failed — wait 10 minutes, try full cycle once more
    print("  All models failed. Waiting 10 minutes before final retry...")
    time.sleep(600)
    result = _try_models()
    if result:
        return result

    raise RuntimeError("All Gemini models failed after 2 full passes")


def parse_json(text: str) -> dict:
    cleaned = re.sub(r"```(?:json)?\n?|```", "", text).strip()
    return json.loads(cleaned)


def load_recent_topics(n: int = 30) -> list:
    if TOPICS_FILE.exists():
        return json.loads(TOPICS_FILE.read_text())[-n:]
    return []


def save_topic(topic: str) -> None:
    topics = json.loads(TOPICS_FILE.read_text()) if TOPICS_FILE.exists() else []
    topics.append(topic)
    TOPICS_FILE.write_text(json.dumps(topics, indent=2))


SHORT_PROMPT = """You are the head writer for StoicElderWisdom — a YouTube Shorts channel for men 45–65.
Tone: direct, warm, hits a nerve. Every word earns its place.

Topics used recently — pick something DIFFERENT: {recent_topics}

BANNED PHRASES: "In today's world", "It's important to remember", "The Stoics believed that",
"Ancient wisdom tells us", "As men, we", "Life is short", "You are not alone", "Modern society"

SCRIPT RULES:
- Hook: first 3 seconds, MAX 10 words, names something SPECIFIC this man has felt
  Good: "You stopped expecting things to get better. When did that happen?"
  Bad: "Most men your age are struggling."
- NEVER start with a philosopher's name
- Every sentence MAX 12 words. Short punchy paragraphs
- Name ONE philosopher exactly ONCE mid-script
- Second-to-last sentence: spoken CTA — "The full breakdown is in today's video — link in the description."
- Final sentence: one quiet reframe the viewer carries with them
- Approximately 130 words total
- No double slashes (//), no asterisks (**), no markdown

IMAGE: Dramatic, high contrast, vertical 9:16. Choose the style that hits hardest for this topic:
1 = extreme close-up of an older man's weathered face, half in shadow, intense side lighting
2 = older man silhouetted at a rain-streaked window, warm amber light behind
3 = weathered hands gripping the edge of a table, candlelight, tension in the fingers
4 = lone figure standing at the edge of a cliff or hilltop, storm clouds behind
5 = ancient marble bust cracking apart, warm light on one side, darkness on the other

Return ONLY valid JSON, no markdown:

{{
  "topic": "3-5 word topic name",
  "script": "~130 words. Hook — Stoic principle — spoken CTA — quiet reframe. No markdown.",
  "image_prompt": "Detailed cinematic vertical 9:16 image prompt. High contrast, dramatic lighting, emotionally striking.",
  "thumbnail_text": "2-4 words ALL CAPS for thumbnail overlay — a gut-punch curiosity hook. Use \\n to split 2 words per line. Examples: THEY LIED\\nTO YOU / WHY YOU\\nCAN'T SLEEP / STOP\\nWAITING",
  "youtube": {{
    "title": "Under 55 chars — use a clickbait pattern that stops scrolling: 'Why Men Over 50 Feel X', 'Stop Doing X After 50', 'The Truth About X Nobody Tells You', 'What X Does to Men Over 50'. No #Shorts in title.",
    "description": "One punchy sentence mirroring the hook.\\n\\nFull video: https://www.youtube.com/@StoicElderWisdom\\n\\nFREE CHAPTER: stoicelderwisdom.kit.com/free-chapter\\n\\n#Shorts #Stoicism #StoicElderWisdom #MarcusAurelius #WisdomForMen #MenOver50 #StoicPhilosophy #AgingWell",
    "tags": ["shorts", "stoicism", "stoic elder wisdom", "marcus aurelius", "wisdom for men", "men over 50", "stoic philosophy", "aging well", "masculinity", "stoic wisdom"]
  }}
}}"""


TEASER_PROMPT = """You are writing a 55-second teaser Short for a StoicElderWisdom YouTube video.
Your job: make men 45-65 desperate to watch the full video. Tease the idea — don't resolve it.

TODAY'S FULL VIDEO:
Title: {video_title}
Hook: {video_hook}
Topic: {video_topic}

SCRIPT RULES:
- Open with the most emotionally raw version of the video's core question (MAX 10 words)
- Build for 40 seconds — tease the insight without giving it away
- DO NOT resolve the tension — leave them needing the answer
- Final line: "The full video is in the description. Watch it tonight." (natural, not salesy)
- 120-130 words total. No markdown. No double slashes. No asterisks.
- Tone: urgent but measured. Like someone saying "you need to hear this."

IMAGE: Dramatic, high contrast, vertical 9:16. One of:
1 = extreme close-up older man's face, one eye in shadow, intense expression
2 = silhouette of a man standing alone in a doorway, bright light behind him
3 = hands holding a photograph, blurred, candlelight
4 = empty chair at a table set for two
5 = a man's shadow on an empty road at dusk

Return ONLY valid JSON, no markdown:

{{
  "topic": "3-5 word topic label",
  "script": "120-130 words. Opens with raw question. Teases insight. Ends with CTA to full video.",
  "image_prompt": "Detailed cinematic vertical 9:16 image. High contrast, emotionally charged, dramatic lighting.",
  "thumbnail_text": "2-4 words ALL CAPS — creates urgency or curiosity. Split with \\n. Examples: WATCH\\nTHIS / YOU\\nNEED THIS / BEFORE\\nTONIGHT",
  "youtube": {{
    "title": "Under 55 chars — make them feel like they're missing something right now. Clickbait patterns: 'Watch This Before You Sleep Tonight', 'This Changes How You See Everything', 'If You're Over 50 Watch This Now'",
    "description": "One punchy line.\\n\\nFull video: https://www.youtube.com/watch?v={video_id}\\n\\nFREE CHAPTER: stoicelderwisdom.kit.com/free-chapter\\n\\n#Shorts #Stoicism #StoicElderWisdom #MenOver50",
    "tags": ["shorts", "stoicism", "stoic elder wisdom", "wisdom for men", "men over 50", "stoic wisdom"]
  }}
}}}"""


# ── per-short steps ───────────────────────────────────────────────────────────────
def generate_voiceover(script: str, idx: int) -> Path:
    mp3_path = OUTPUT_DIR / f"short_{idx}_audio.mp3"

    # Try Kokoro first
    try:
        from kokoro import KPipeline
        import soundfile as sf
        wav_path = OUTPUT_DIR / f"short_{idx}_audio.wav"
        print(f"  Generating voiceover (Kokoro am_michael)...")
        pipeline = KPipeline(lang_code="a")
        chunks   = [audio for _, _, audio in pipeline(script, voice="am_michael", speed=0.82)]
        sf.write(str(wav_path), np.concatenate(chunks), 24000)
        subprocess.run([
            "ffmpeg", "-y", "-i", str(wav_path),
            "-codec:a", "libmp3lame", "-b:a", "128k", str(mp3_path),
        ], check=True, capture_output=True)
        wav_path.unlink(missing_ok=True)
        print(f"    Saved: {mp3_path}")
        return mp3_path
    except Exception as e:
        print(f"    Kokoro failed: {e} — falling back to Edge TTS")

    # Fallback: Edge TTS
    print(f"  Generating voiceover (Edge TTS {EDGE_VOICE})...")
    async def _edge():
        import edge_tts
        comm = edge_tts.Communicate(script, EDGE_VOICE, rate=EDGE_RATE, pitch=EDGE_PITCH)
        await comm.save(str(mp3_path))
    asyncio.run(_edge())
    print(f"    Saved: {mp3_path}")
    return mp3_path


def generate_image(prompt: str, idx: int, api_key: str) -> Path:
    import base64, requests as _req, urllib.parse
    img_path = OUTPUT_DIR / f"short_{idx}_image.jpg"

    # Try Imagen first
    print(f"  Generating image (Imagen)...")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/imagen-3.0-generate-002:predict?key={api_key}"
    )
    payload = {
        "instances": [{"prompt": prompt}],
        "parameters": {"sampleCount": 1, "aspectRatio": "9:16",
                       "outputMimeType": "image/jpeg"},
    }
    for attempt in range(1, 3):
        try:
            resp = _req.post(url, json=payload, timeout=120)
            resp.raise_for_status()
            b64 = resp.json()["predictions"][0]["bytesBase64Encoded"]
            img_path.write_bytes(base64.b64decode(b64))
            print(f"    Saved (Imagen): {img_path}")
            time.sleep(3)
            return img_path
        except Exception as e:
            print(f"    Imagen attempt {attempt} failed: {e}")
            if attempt < 2:
                time.sleep(10)

    # Fallback 1: Pollinations (try free models in order)
    encoded = urllib.parse.quote(prompt[:500])   # cap prompt length
    for poll_model in ["turbo", "flux-schnell", "stable-diffusion-xl-base-1.0"]:
        print(f"  Falling back to Pollinations ({poll_model})...")
        poll_url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=576&height=1024&model={poll_model}&nologo=true&seed={idx * 7331}"
        )
        try:
            resp = _req.get(poll_url, timeout=90)
            if resp.status_code == 402:
                print(f"    {poll_model} requires payment — trying next...")
                continue
            resp.raise_for_status()
            img_path.write_bytes(resp.content)
            print(f"    Saved (Pollinations/{poll_model}): {img_path}")
            return img_path
        except Exception as e:
            print(f"    Pollinations/{poll_model} failed: {e}")

    # Fallback 2: Hugging Face Inference API (free, no key needed for public models)
    print(f"  Falling back to Hugging Face (SDXL)...")
    hf_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    short_prompt = prompt[:300]
    for attempt in range(1, 4):
        try:
            resp = _req.post(hf_url, json={"inputs": short_prompt,
                             "parameters": {"width": 576, "height": 1024}}, timeout=120)
            if resp.status_code == 503:   # model loading
                print(f"    HF model loading, waiting 20s...")
                time.sleep(20)
                continue
            resp.raise_for_status()
            img_path.write_bytes(resp.content)
            print(f"    Saved (HuggingFace): {img_path}")
            return img_path
        except Exception as e:
            print(f"    HuggingFace attempt {attempt} failed: {e}")
            if attempt < 3:
                time.sleep(15)
            if attempt < 3:
                time.sleep(10)

    raise RuntimeError(f"Image generation failed for short {idx}")


def generate_subtitles(audio_path: Path, idx: int) -> Path:
    import whisper
    srt_path = OUTPUT_DIR / f"short_{idx}.srt"
    print(f"  Transcribing audio for subtitles...")
    model  = whisper.load_model("base")
    result = model.transcribe(str(audio_path), word_timestamps=True, language="en")

    def fmt(t: float) -> str:
        h  = int(t // 3600)
        m  = int((t % 3600) // 60)
        s  = int(t % 60)
        ms = int((t % 1) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    words, cards = [], []
    for seg in result["segments"]:
        for w in seg.get("words", []):
            words.append({"word": w["word"].strip(), "start": w["start"], "end": w["end"]})

    i = 0
    while i < len(words):
        chunk = words[i:i+4]
        cards.append({"text": " ".join(w["word"] for w in chunk),
                      "start": chunk[0]["start"], "end": chunk[-1]["end"]})
        i += 4

    with open(srt_path, "w", encoding="utf-8") as f:
        for n, card in enumerate(cards, 1):
            if card["start"] < SHORT_DURATION:
                f.write(f"{n}\n{fmt(card['start'])} --> {fmt(card['end'])}\n{card['text']}\n\n")

    print(f"    Saved: {srt_path}")
    return srt_path


def build_video(img_path: Path, audio_path: Path, srt_path: Path, idx: int) -> Path:
    video_path  = OUTPUT_DIR / f"short_{idx}_video.mp4"
    srt_escaped = str(srt_path.resolve()).replace("\\", "/").replace(":", "\\:")
    d = SHORT_DURATION * FPS

    vf = (
        f"scale=1920:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"zoompan=z='1.0+0.04*on/{d}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        f":d={d}:s=1080x1920:fps={FPS},"
        f"subtitles='{srt_escaped}'"
        f":force_style='FontName=Georgia,FontSize=26,Bold=1,"
        f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        f"Outline=4,Alignment=2,MarginV=120'"
    )

    print(f"  Building vertical video...")
    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(img_path),
        "-i", str(audio_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(SHORT_DURATION),
        "-shortest", "-movflags", "+faststart",
        str(video_path),
    ], check=True, capture_output=True)
    print(f"    Saved: {video_path}")
    return video_path


# ── Thumbnail ─────────────────────────────────────────────────────────────────────
def generate_short_thumbnail(img_path: Path, thumb_text: str, idx: int) -> Path:
    """Create a bold split-panel thumbnail for the short (1280x720)."""
    try:
        from PIL import Image, ImageDraw, ImageFont, ImageEnhance
    except ImportError:
        return img_path  # skip silently if PIL missing

    GOLD = (201, 168, 76)
    TW, TH = 1280, 720
    thumb_path = OUTPUT_DIR / f"short_{idx}_thumb.jpg"

    # Load short image (576x1024 vertical) — crop to 16:9
    img = Image.open(img_path).convert("RGB")
    scale = max(TW / img.width, TH / img.height)
    img   = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    lx    = (img.width - TW) // 2
    ly    = (img.height - TH) // 2
    img   = img.crop((lx, ly, lx + TW, ly + TH))

    # Brighten image slightly
    img = ImageEnhance.Brightness(img).enhance(0.78)
    img = img.convert("RGBA")

    # Split-panel: solid dark left 58%, fade to transparent
    panel_w = int(TW * 0.58)
    panel   = Image.new("RGBA", img.size, (0, 0, 0, 0))
    pd      = ImageDraw.Draw(panel)
    pd.rectangle([0, 0, panel_w, TH], fill=(10, 6, 2, 230))
    for i in range(130):
        alpha = int(230 * (1 - i / 130))
        pd.rectangle([panel_w + i, 0, panel_w + i + 1, TH], fill=(10, 6, 2, alpha))
    # Bottom strip
    for i in range(85):
        alpha = int(210 * (1 - i / 85))
        pd.rectangle([0, TH - i, TW, TH - i + 1], fill=(8, 4, 2, alpha))

    img = Image.alpha_composite(img, panel).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Gold left stripe + border
    draw.rectangle([0, 0, 7, TH], fill=GOLD)
    draw.rectangle([0, 0, TW - 1, TH - 1], outline=GOLD, width=3)

    # Fonts — reuse same search as main thumbnail
    def _font(path_list, size):
        for p in path_list:
            try:
                from PIL import ImageFont
                return ImageFont.truetype(p, size)
            except Exception:
                continue
        from PIL import ImageFont
        return ImageFont.load_default()

    serif_paths = ["C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf",
                   "C:/Windows/Fonts/cambriab.ttf", "C:/Windows/Fonts/arialbd.ttf"]
    sans_paths  = ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/calibrib.ttf"]

    font_top  = _font(sans_paths,  26)
    font_main = _font(serif_paths, 130)
    font_sub  = _font(sans_paths,  28)

    def stroke_text(d, xy, text, font, fill, sw=5):
        x, y = xy
        for dx in range(-sw, sw + 1):
            for dy in range(-sw, sw + 1):
                if dx or dy:
                    d.multiline_text((x+dx, y+dy), text, font=font,
                                     fill=(0, 0, 0), align="left")
        d.multiline_text((x, y), text, font=font, fill=fill, align="left")

    x = 26
    stroke_text(draw, (x, 36),    "STOIC ELDER WISDOM", font_top,  GOLD, sw=2)
    draw.rectangle([x, 72, x + 300, 75], fill=GOLD)
    stroke_text(draw, (x, 88),    thumb_text,           font_main, (255, 255, 255), sw=6)
    stroke_text(draw, (x, TH-62), "@StoicElderWisdom",  font_sub,  GOLD, sw=2)

    img.save(str(thumb_path), "JPEG", quality=95)
    print(f"    Thumbnail saved: {thumb_path}")
    return thumb_path


def set_thumbnail(youtube, video_id: str, thumb_path: Path) -> None:
    try:
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(str(thumb_path), mimetype="image/jpeg"),
        ).execute()
        print(f"    Thumbnail set.")
    except Exception as e:
        print(f"    Thumbnail upload failed: {e}")


# ── YouTube ────────────────────────────────────────────────────────────────────────
def get_youtube():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow  = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def post_comment(youtube, short_id: str) -> None:
    # Link to today's main video if available, otherwise the channel
    main_url = "https://www.youtube.com/@StoicElderWisdom"
    try:
        meta_file = Path("output/video_meta.json")
        if meta_file.exists():
            vid_id = json.loads(meta_file.read_text()).get("video_id", "")
            if vid_id:
                main_url = f"https://www.youtube.com/watch?v={vid_id}"
    except Exception:
        pass

    text = (
        f"Watch the full video here 👉 {main_url}\n\n"
        f"📖 FREE CHAPTER — \"What the Stoics Knew About Getting Old\"\n"
        f"The Stoics didn't write for young men chasing success. "
        f"They wrote for men trying to live and die well.\n"
        f"Get Chapter 5 free → stoicelderwisdom.kit.com/free-chapter\n\n"
        f"Subscribe for weekly stoic wisdom 🔔"
    )
    try:
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": short_id,
                    "topLevelComment": {"snippet": {"textOriginal": text}},
                }
            },
        ).execute()
        print(f"  Comment posted.")
    except Exception as e:
        print(f"  Comment post failed: {e}")


def upload_short(youtube, video_path: Path, meta: dict) -> str:
    raw_title = meta["title"]
    title = (raw_title[:52] + " #Shorts") if len(raw_title) <= 52 else (raw_title[:48] + "… #Shorts")
    body = {
        "snippet": {
            "title":       title,
            "description": meta["description"],
            "tags":        meta["tags"],
            "categoryId":  "27",
        },
        "status": {
            "privacyStatus":           "public",
            "selfDeclaredMadeForKids": False,
        },
    }
    media       = MediaFileUpload(str(video_path), mimetype="video/mp4",
                                  resumable=True, chunksize=8*1024*1024)
    request     = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response    = None
    retries     = 0
    MAX_RETRIES = 10
    while response is None:
        try:
            status, response = request.next_chunk()
            retries = 0
            if status:
                print(f"  Upload: {int(status.progress()*100)}%", end="\r")
        except (TimeoutError, socket.timeout, ConnectionError, OSError) as e:
            retries += 1
            if retries > MAX_RETRIES:
                raise
            wait = min(2 ** retries, 120)
            print(f"\n  Network error ({type(e).__name__}), retry {retries}/{MAX_RETRIES} in {wait}s...")
            time.sleep(wait)
    short_id = response["id"]
    print(f"\n  Live: https://www.youtube.com/shorts/{short_id}")
    return short_id


# ── main ──────────────────────────────────────────────────────────────────────────
def load_video_info() -> dict:
    """Load today's main video info for teaser mode."""
    info = {}
    for f in ["output/video_meta.json", "output/video_info.json"]:
        try:
            if Path(f).exists():
                info.update(json.loads(Path(f).read_text(encoding="utf-8")))
        except Exception:
            pass
    return info


def main():
    mode = "TEASER" if TEASER_MODE else "STANDALONE"
    print(f"\nSTOICELDERWISDOM SHORTS PIPELINE — STARTING ({mode})")
    print(f"Generating {NUM_SHORTS} Short(s)...\n")
    tg(f"🎬 <b>Shorts starting ({mode})</b> — {NUM_SHORTS} short(s)...")

    api_key = load_api_key()
    youtube = get_youtube()
    total_start = time.time()
    used_in_this_run = []

    # Load today's video info for teaser mode
    video_info = load_video_info()
    video_id    = video_info.get("video_id", "")
    video_title = video_info.get("title",    "StoicElderWisdom")
    video_hook  = video_info.get("hook",     "")
    video_topic = video_info.get("topic",    "")

    for i in range(1, NUM_SHORTS + 1):
        print(f"\n{'='*60}")
        print(f"  SHORT {i}/{NUM_SHORTS} ({mode})")
        print(f"{'='*60}")

        print(f"  Calling Gemini...")
        if TEASER_MODE:
            prompt = TEASER_PROMPT.format(
                video_title=video_title,
                video_hook=video_hook,
                video_topic=video_topic,
                video_id=video_id,
            )
        else:
            recent     = load_recent_topics() + used_in_this_run
            recent_str = ", ".join(f'"{t}"' for t in recent[-30:]) if recent else "none yet"
            prompt     = SHORT_PROMPT.format(recent_topics=recent_str)

        data = None
        for json_attempt in range(1, 4):
            raw = call_gemini(prompt, api_key)
            try:
                # Extract outermost JSON object — ignore trailing text
                cleaned = re.sub(r"```(?:json)?\n?|```", "", raw).strip()
                start = cleaned.find("{")
                end   = cleaned.rfind("}") + 1
                data  = json.loads(cleaned[start:end])
                break
            except json.JSONDecodeError as e:
                if json_attempt < 3:
                    print(f"  JSON parse error (attempt {json_attempt}/3), retrying... ({e})")
                    time.sleep(5)
                else:
                    raise

        print(f"  Topic: {data['topic']}")
        script        = clean_script(data["script"])
        thumb_text    = data.get("thumbnail_text", "WATCH\nNOW")

        audio = generate_voiceover(script, i)
        img   = generate_image(data["image_prompt"], i, api_key)
        srt   = generate_subtitles(audio, i)
        vid   = build_video(img, audio, srt, i)

        # Generate thumbnail
        thumb = generate_short_thumbnail(img, thumb_text, i)

        print(f"  Uploading Short...")
        short_id  = upload_short(youtube, vid, data["youtube"])
        short_url = f"https://www.youtube.com/shorts/{short_id}"

        # Set thumbnail
        if thumb.exists():
            set_thumbnail(youtube, short_id, thumb)

        post_comment(youtube, short_id)
        tg(f"✅ Short live: <a href='{short_url}'>{data['topic']}</a>")

        if not TEASER_MODE:
            save_topic(f"[SHORT] {data['topic']}")
            used_in_this_run.append(f"[SHORT] {data['topic']}")

        if i < NUM_SHORTS:
            print(f"  Waiting 10s before next Short...")
            time.sleep(10)

    elapsed = time.time() - total_start
    print(f"\n{'='*60}")
    print(f"  SHORTS PIPELINE COMPLETE in {elapsed/60:.1f} minutes")
    print(f"  {NUM_SHORTS} Short(s) are live on YouTube.")
    print(f"{'='*60}\n")
    tg(f"🎉 <b>{NUM_SHORTS} Short(s) live in {elapsed/60:.1f} min!</b>")


if __name__ == "__main__":
    main()
