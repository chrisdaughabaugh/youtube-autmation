"""
animate_images.py — StoicElderWisdom
Animates generated images into short video clips using Google Veo 2.
Input:  generated_images/*.jpg
Output: generated_clips/*.mp4  (5-second animated clips)
Falls back gracefully — if Veo fails, assemble_video.py uses static images.
"""
import base64
import json
import os
import time
import requests
from pathlib import Path

IMAGES_DIR = Path("generated_images")
CLIPS_DIR  = Path("generated_clips")
CLIPS_DIR.mkdir(exist_ok=True)

CLIP_DURATION = 5  # seconds per clip


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


# Slow, contemplative animation prompts mapped by image label keyword
ANIMATION_PROMPTS = {
    "window":   "Slow golden light shifts across the room. Dust motes drift in the beam. The man breathes slowly, barely moving. Camera drifts almost imperceptibly closer.",
    "lake":     "Mist rises gently from the still water. A barely perceptible ripple moves outward. The reflection shimmers with soft light. Camera slowly pulls back.",
    "hands":    "The hands rest still. Candlelight flickers gently. A subtle breath lifts the chest. Pages settle with a whisper.",
    "bust":     "Candlelight flickers, casting slow shifting shadows across the marble. The background breathes in deep amber and shadow.",
    "forest":   "Leaves drift slowly from the trees. Golden light filters through, shifting as branches sway almost imperceptibly. The man walks in slow, unhurried steps.",
    "fireplace":"Embers pulse with slow orange glow. A single flame dances lazily. Smoke curls upward. The room breathes with warmth.",
    "ruins":    "Long shadows shift almost imperceptibly as the sun rises. A breath of wind stirs dust across the ancient stones.",
    "fire":     "The fire crackles slowly. Embers drift upward. The man's face is lit in slow warm pulses. Mountains are dark and still behind him.",
    "library":  "The candle flame sways gently. Warm light pulses across old book spines. Deep shadows breathe in the corners.",
    "mountain": "Morning mist drifts slowly between the ridges. Light shifts from grey to gold. The landscape breathes with ancient stillness.",
    "mirror":   "Morning light shifts softly. The man holds his gaze in the mirror. Breath visible in the cool air.",
    "bench":    "Autumn leaves drift down slowly behind the man. He sits perfectly still. The empty bench beside him is quietly present.",
    "journal":  "Morning light shifts across the open pages. Steam rises slowly from the coffee cup. The pen rests still.",
    "sunset":   "The sun descends slowly behind the hills. The tree silhouette holds perfectly still. The sky deepens from gold to amber.",
    "default":  "Slow, contemplative cinematic drift. Barely perceptible camera movement. Warm light shifts gently. The mood is still, unhurried, ancient.",
}


def get_animation_prompt(label: str) -> str:
    label_lower = label.lower()
    for keyword, prompt in ANIMATION_PROMPTS.items():
        if keyword in label_lower:
            return prompt
    return ANIMATION_PROMPTS["default"]


def animate_image_veo(image_path: Path, api_key: str) -> Path | None:
    """Submit image to Veo 2 and poll until clip is ready. Returns clip path or None."""
    clip_path = CLIPS_DIR / f"{image_path.stem}.mp4"
    if clip_path.exists():
        print(f"  Skipping (already exists): {clip_path.name}")
        return clip_path

    animation_prompt = get_animation_prompt(image_path.stem)
    image_b64 = base64.b64encode(image_path.read_bytes()).decode()

    # Submit to Veo 2
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/veo-2.0-generate-001:predictLongRunning?key={api_key}"
    )
    payload = {
        "instances": [{
            "prompt": animation_prompt,
            "image":  {"bytesBase64Encoded": image_b64, "mimeType": "image/jpeg"},
        }],
        "parameters": {
            "aspectRatio":    "16:9",
            "durationSeconds": CLIP_DURATION,
            "numberOfVideos":  1,
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code == 429:
            print(f"  Veo rate limited — waiting 60s...")
            time.sleep(60)
            resp = requests.post(url, json=payload, timeout=60)
        if resp.status_code not in (200, 202):
            print(f"  Veo submit failed ({resp.status_code}): {resp.text[:200]}")
            return None
        operation_name = resp.json().get("name")
        if not operation_name:
            print(f"  Veo: no operation name in response")
            return None
    except Exception as e:
        print(f"  Veo submit error: {e}")
        return None

    # Poll until done (max 5 minutes)
    poll_url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}?key={api_key}"
    print(f"  Veo job started — polling...")
    for attempt in range(30):
        time.sleep(10)
        try:
            status = requests.get(poll_url, timeout=30)
            data   = status.json()
            if data.get("done"):
                videos = data.get("response", {}).get("videos", [])
                if not videos:
                    print(f"  Veo done but no video in response")
                    return None
                video_b64 = videos[0].get("bytesBase64Encoded", "")
                if not video_b64:
                    print(f"  Veo: empty video data")
                    return None
                clip_path.write_bytes(base64.b64decode(video_b64))
                return clip_path
            if data.get("error"):
                print(f"  Veo error: {data['error'].get('message', 'unknown')}")
                return None
        except Exception as e:
            print(f"  Veo poll error (attempt {attempt+1}): {e}")

    print(f"  Veo timed out after 5 minutes")
    return None


def main():
    api_key     = load_api_key()
    image_files = sorted(IMAGES_DIR.glob("*.jpg")) + sorted(IMAGES_DIR.glob("*.png"))

    if not image_files:
        print(f"No images found in {IMAGES_DIR}/ — skipping animation step")
        return

    print(f"Animating {len(image_files)} images with Veo 2...\n")
    success = 0
    for img in image_files:
        print(f"Animating: {img.name}")
        clip = animate_image_veo(img, api_key)
        if clip:
            print(f"  Saved: {clip.name}")
            success += 1
        else:
            print(f"  Failed — assemble_video.py will use static image as fallback")
        time.sleep(2)

    print(f"\nAnimation complete: {success}/{len(image_files)} clips generated.")
    if success == 0:
        print("No clips generated — pipeline will use static images.")


if __name__ == "__main__":
    main()
