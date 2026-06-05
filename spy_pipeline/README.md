# Spy-Thriller Video Pipeline

Automated 9:16 vertical video pipeline for YouTube Shorts / TikTok.
Generates original stick-figure espionage stories with AI narration, bold captions, and cinematic music.

## Stack

| Component | Tool | Cost |
|-----------|------|------|
| Story generation | Groq API (Llama 3.3 70B) | Free tier |
| Text-to-speech | Microsoft Edge TTS (`edge-tts`) | Free |
| Visuals | Pillow (procedural stick figures) | Free |
| Assembly | MoviePy + ffmpeg | Free |
| Music | Your local royalty-free tracks | Free |

---

## Install

**Requirements:** Python 3.10+, ffmpeg

```bash
cd spy_pipeline
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## API Keys

1. Get a free Groq API key at https://console.groq.com
2. Copy `.env.template` to `.env`
3. Fill in `GROQ_API_KEY`

```bash
cp .env.template .env
# edit .env and paste your key
```

---

## Music & Fonts

**Music:** Drop royalty-free `.mp3` or `.wav` files into `assets/music/`.
Good free sources:
- https://pixabay.com/music/ (search "cinematic spy")
- YouTube Audio Library (filter: dark / suspense)
- https://freesound.org (filter: CC0)

**Fonts (optional):** Drop a bold `.ttf` into `assets/fonts/`. If empty, the pipeline uses the system DejaVu Bold font.

---

## Usage

```bash
cd spy_pipeline
source venv/bin/activate

# Single video (random theme)
python main.py single

# Single video (specific theme)
python main.py single --theme "the mole"

# Batch (5 videos)
python main.py batch --count 5

# Run one stage at a time
python main.py stage story --theme "the defector"
python main.py stage voice  --dir output/20240101_120000_the_defector
python main.py stage visuals --dir output/20240101_120000_the_defector
python main.py stage assemble --dir output/20240101_120000_the_defector
python main.py stage metadata --dir output/20240101_120000_the_defector
```

---

## Output Structure

Each video gets its own timestamped folder under `output/`:

```
output/20240101_120000_the_mole/
  story.json          # AI-generated story
  timing.json         # per-segment audio timing
  narration.mp3       # full narration track
  video.mp4           # final 9:16 MP4
  metadata.json       # titles, description, hashtags
  metadata.txt        # human-readable version
  audio_clips/        # per-scene audio clips
  frames/             # per-scene PNG images
```

---

## Swapping the TTS Provider

The TTS is isolated in `modules/voiceover.py` behind `generate_speech(text, out_path) -> float`.

To swap to ElevenLabs:
1. `pip install elevenlabs`
2. Add `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID` to `.env`
3. Replace the `_synthesize` function body in `voiceover.py`

To swap to OpenAI TTS:
1. `pip install openai`
2. Add `OPENAI_API_KEY` to `.env`
3. Replace the `_synthesize` function body in `voiceover.py`

---

## Topics Bank

Edit `topics.txt` — one theme per line. The pipeline picks randomly when no `--theme` is given.

---

## Legal / Content Policy

- All content is **100% original fiction** — no real people, no real agencies, no real franchises
- Violence is stylized stick-figure level, never graphic
- Music must be royalty-free; the pipeline only reads from your local `assets/music` folder
