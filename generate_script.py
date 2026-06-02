"""
generate_script.py — StoicElderWisdom
Uses Gemini to generate a full video package for men 45–65.
Tone: warm, deep, calm — like a wise older man talking to an equal.
"""
import json
import os
import re
import sys
import time
import requests
from pathlib import Path

OUTPUT_DIR  = Path("output")
TOPICS_FILE = Path("posted_topics.json")

OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "thumbnails").mkdir(exist_ok=True)


# ── Topic bank ─────────────────────────────────────────────────────────────────
TOPIC_BANK = [
    # Round 1 — original
    "Making peace with a life that didn't go as planned",
    "What Marcus Aurelius said about growing old with dignity",
    "The stoic guide to losing someone you love",
    "How to find purpose when your career is behind you",
    "Carrying regret — the stoic way to finally let it go",
    "What Seneca said about the shortness of time",
    "How Marcus Aurelius faced death without fear",
    "The stoic way to handle an ungrateful adult child",
    "When the life you built feels like it wasn't enough",
    "Epictetus on finding peace when life didn't go your way",
    "The stoic answer to loneliness after 50",
    "How to stop living in the past — ancient wisdom",
    "What the stoics said about legacy and being remembered",
    "Finding meaning in the years you have left",
    "The stoic guide to a difficult marriage",
    "Why silence becomes powerful as you get older",
    "How Marcus Aurelius dealt with betrayal and ingratitude",
    "Stoic wisdom for men going through loss of identity",
    "What Seneca said about wasted years — and what to do now",
    "The one stoic principle that changes how you see aging",
    # Round 2 — search-intent, specific, emotionally direct
    "Why men over 50 feel invisible — and what Seneca said about it",
    "The quiet regret most men carry into their 60s",
    "How to stop being angry about the life you didn't get",
    "What Marcus Aurelius wrote the year his son died",
    "When you realize you've been living for everyone else",
    "The stoic answer to feeling like you've wasted your life",
    "Why men don't talk about being lonely — and why they should",
    "What Epictetus said about men who gave everything to their work",
    "How to make peace with the version of you that failed",
    "Seneca's letter to a man running out of time",
    "What to do when your children don't respect you",
    "The grief no one warns you about after retirement",
    "How to live the years you have left without regret",
    "Why most men never find peace — and the stoic fix",
    "What the stoics said about a marriage that lost its warmth",
    "The moment Marcus Aurelius admitted he was afraid",
    "How to carry loss without letting it define you",
    "What Epictetus taught men who felt trapped by their own choices",
    "The stoic cure for a restless mind at 3am",
    "Why the second half of life can be the most meaningful",
]


# ── API ────────────────────────────────────────────────────────────────────────
def load_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    env = Path(".env")
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise ValueError("GEMINI_API_KEY not found in environment or .env file")


MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

def call_gemini(prompt: str, api_key: str, retries: int = 3) -> str:
    """Call Gemini with full retry resilience.
    - 503 (service down): wait 30s/60s/90s then move to next model
    - 429 (rate limit): wait 60s/120s/180s then move to next model
    - If ALL models fail on first pass: wait 10 min, do a full second pass
    """
    def _try_models() -> str | None:
        for model in MODELS:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/"
                f"models/{model}:generateContent?key={api_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.9, "maxOutputTokens": 65536},
            }
            for attempt in range(1, retries + 1):
                try:
                    resp = requests.post(url, json=payload, timeout=180)
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
                        print(f"  WARNING: {model} hit token limit — trying next model...")
                        break
                    print(f"  Using model: {model}  (finishReason={finish})")
                    return text
                except Exception as e:
                    print(f"  {model} attempt {attempt} failed: {e}")
                    if attempt < retries:
                        time.sleep(10)
            print(f"  {model} exhausted, trying next model...")
        return None

    result = _try_models()
    if result:
        return result

    print("  All models failed. Waiting 10 minutes before final retry...")
    time.sleep(600)
    result = _try_models()
    if result:
        return result

    raise RuntimeError("All Gemini models failed after 2 full passes")


def parse_json(text: str) -> dict:
    # Strip markdown fences
    cleaned = re.sub(r"```(?:json)?\n?|```", "", text).strip()
    # Extract just the outermost JSON object — ignore any trailing text Gemini appends
    start = cleaned.find("{")
    end   = cleaned.rfind("}") + 1
    if start == -1 or end == 0:
        raise json.JSONDecodeError("No JSON object found", cleaned, 0)
    return json.loads(cleaned[start:end])


# ── Topic tracking ─────────────────────────────────────────────────────────────
def load_used_topics() -> list:
    if TOPICS_FILE.exists():
        text = TOPICS_FILE.read_text(encoding="utf-8-sig").strip()
        if text:
            try:
                return json.loads(text)
            except Exception:
                pass
    return []


def get_next_topic() -> str:
    used = [t.lower() for t in load_used_topics()]
    for topic in TOPIC_BANK:
        if topic.lower() not in used:
            return topic
    return "Finding peace and meaning in the second half of life"


def save_topic(topic: str) -> None:
    topics = load_used_topics()
    topics.append(topic)
    TOPICS_FILE.write_text(json.dumps(topics, indent=2), encoding="utf-8")


# ── Prompt ─────────────────────────────────────────────────────────────────────
PROMPT = """You are the head writer for StoicElderWisdom (@StoicElderWisdom) — a YouTube channel for men 45–65+ asking deeper questions about life, legacy, and peace.

YOUR VIEWER: A man between 45 and 65. He worked hard his whole life and is asking "was it worth it?" He has lost people — parents, friends, maybe a marriage. He feels invisible in a culture obsessed with youth. He wants peace more than success. He searches YouTube at night when he can't sleep. He respects depth, hates hype, has no patience for fluff. He can tell immediately when something is AI-generated filler.

Write every script as if you are sitting across from this man at a quiet table. Speak to him like an equal who has also lived.

TOPIC FOR THIS VIDEO: {topic}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BANNED PHRASES — never use any of these:
"In today's world", "In today's fast-paced world", "It's important to remember",
"At the end of the day", "This is a journey", "You are not alone",
"It's okay to", "The good news is", "Take a moment", "Remember that",
"As men, we", "Let that sink in", "That's powerful", "Life is short",
"Modern society", "The world today", "We live in a time",
"Stoic philosophy teaches us", "The Stoics believed that", "Ancient wisdom tells us",
"This ancient philosophy", "These timeless teachings"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCRIPT RULES (no exceptions):
- Hook: first 3 seconds, MAX 10 words. Must name a SPECIFIC thing this man has felt — not a vague truth. A moment he recognizes from his own life.
  Good examples: "You stopped expecting things to get better. When did that happen?"
                 "Your father never told you he was proud of you."
                 "You built everything they asked for. And it still wasn't enough."
  Bad examples: "Most men your age are struggling." / "Life can be difficult."
- NEVER start with a philosopher's name
- NEVER sound like motivation content — no energy, no urgency, no uplift
- Every sentence MAX 12 words
- Short paragraphs — 2 to 3 sentences each
- Include ONE specific stoic principle, grounded in a REAL historical moment. Give context: where the philosopher was, what was happening in his life, why it matters. This is not a quote dump — it's a story.
- Name the philosopher ONCE, naturally mid-script (never at start or end)
- Around the 2/3 mark of the script, include ONE natural verbal mention of the free chapter. It must sound like a trusted recommendation, not an ad. Example: "I wrote a short book on this. Chapter 5 is free in the description — it goes deeper than I can here." Keep it one sentence. Weave it into the content naturally.
- Just before the final thought: ONE warm like/subscribe line — brief, genuine, human. Example: "If this hit something real, a like helps this reach the men who need it." Never corporate. One sentence only.
- End with ONE thought the viewer can carry tonight — a reframe, not a task. Something he'll still be thinking about at 2am.
- Word count: 900–1200 words total
- Mark pauses with // in the script
- Mark emphasis words with **bold** in the script
- NEVER say: grind, hustle, discipline, crush it, level up, morning routine, toxic masculinity, self-care, healing journey, show up, growth mindset
- ALWAYS feel: wise, specific, unhurried, real — like a campfire conversation with a man who has lived through something

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TITLE RULES — generate exactly 3 options that a real man would click at 11pm:
- Titles must feel like something he already suspects is true — not a promise of advice
- Use plain, direct language. No colons unless they add tension.
- Think about what this man would actually TYPE into YouTube at night
- Format A: Specific philosopher + specific emotional truth (e.g. "What Marcus Aurelius Wrote the Year His Son Died")
- Format B: The exact thing he feels, stated plainly (e.g. "You Gave Everything. It Still Wasn't Enough.")
- Format C: A question he's been afraid to ask (e.g. "Did You Spend Your Life on the Wrong Things?")
- FORBIDDEN title patterns: anything with "The Stoic Way to...", "Ancient Wisdom for...", "X Things Stoics Know", generic self-help phrasing
- Mark the best one with best: true

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
THUMBNAIL RULES:
- Dark warm background: deep charcoal, navy, or forest green
- Gold accent: #C9A84C
- MAX 4 words text overlay — must create a CURIOSITY GAP or hit a nerve, not label a theme
  Think: what 4 words would make a 55-year-old man stop scrolling at midnight?
  Good: "YOU GAVE\nENOUGH", "STOP\nWAITING", "IT STILL\nCOUNTS", "NOT TOO\nLATE", "YOU WERE\nRIGHT", "THEY WERE\nWRONG"
  Bad: "STOIC WISDOM", "AGING WELL", "INNER PEACE", "LIFE PURPOSE", "IT IS PEACE"
  Format: use \n to split across 2 lines. 2 words per line reads biggest at thumbnail size.
- Focal image: older man (silhouette or from behind), ancient bust, single candle, open weathered book, fog over still water
- Feel: like the cover of a book you'd trust — not a YouTube thumbnail

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESCRIPTION RULES:
- First 2 sentences mirror the emotional hook — pull the viewer in
- Third sentence states what this video gives them
- Naturally weave in: stoic wisdom, marcus aurelius, stoicism for men, {topic_keyword}, seneca, epictetus, men over 50, midlife, legacy, purpose after 50
- End with EXACTLY: "Subscribe to StoicElderWisdom — ancient principles for men who've earned their perspective."
- 10 relevant hashtags — mix high-volume and niche
- Total 150–200 words

IMAGE PROMPTS:
Generate 15 cinematic image prompts. Visual style for this audience:
- Slow, warm, contemplative — never energetic or dramatic
- Nature: forests at dusk, still water at dawn, autumn leaves on stone paths, mountain mist, morning fog over fields
- Human: older man alone at a window (seen from behind), weathered hands holding a book or mug, lone figure walking a quiet wooded path, man sitting by a low fire
- Architecture: old stone buildings in soft light, candlelit study with scattered books, ancient library shelves, Roman ruins at golden hour
- Color palette: warm amber, slightly desaturated film grain feel, golden hour, deep shadow with warm highlights
- Avoid: gym footage, city streets, young people, bright energetic scenes, stock-photo clichés
- Vary the framing: some extreme close-ups (hands, candle flame, book page), some wide landscapes, some medium interiors

IMPORTANT — image 10 must ALWAYS be a thumbnail hero image:
Label it "10_close_up_face" and make it a dramatic extreme close-up of an older man's weathered face (late 50s/60s). He should be looking slightly off-camera with a pensive, quiet expression — not sad, not happy, just deeply thoughtful. Side lighting: warm amber on one half of his face, deep shadow on the other. Dark background on the LEFT side of the frame (where text will be placed). The face fills the RIGHT two-thirds of the frame. Cinematic 16:9. No text. High contrast. This is specifically designed to be used as a YouTube thumbnail background.

Return ONLY valid JSON — no markdown, no text outside the JSON:

{{
  "topic": "short topic label (3-6 words)",
  "hook": "The hook line exactly as it appears at the start of the script (MAX 10 words)",
  "script": "Full 900-1200 word narration script. Use // for pauses. Use **word** for emphasis. Short paragraphs. Specific historical context for philosopher. Like/subscribe line before final thought. End with a perspective shift, not a task.",
  "overlays": [
    {{"timestamp": "0:00-0:04", "text": "MAX 6 WORDS"}},
    {{"timestamp": "0:04-0:08", "text": "NEXT OVERLAY"}},
    {{"timestamp": "0:08-0:12", "text": "NEXT OVERLAY"}},
    {{"timestamp": "0:12-0:16", "text": "NEXT OVERLAY"}},
    {{"timestamp": "0:16-0:20", "text": "NEXT OVERLAY"}},
    {{"timestamp": "0:20-0:24", "text": "NEXT OVERLAY"}},
    {{"timestamp": "0:24-0:28", "text": "STOIC QUOTE — exact words, held 4 seconds"}},
    {{"timestamp": "0:28-0:32", "text": "NEXT OVERLAY"}},
    {{"timestamp": "0:32-0:36", "text": "NEXT OVERLAY"}},
    {{"timestamp": "0:36-0:40", "text": "NEXT OVERLAY"}},
    {{"timestamp": "0:40-0:44", "text": "NEXT OVERLAY"}},
    {{"timestamp": "0:44-0:48", "text": "NEXT OVERLAY"}},
    {{"timestamp": "0:48-0:52", "text": "FINAL OVERLAY — a quiet question, not a call to action"}}
  ],
  "broll": [
    {{"timestamp": "0:00", "shot": "specific slow cinematic shot description", "mood": "contemplative/warm", "search": "pexels search term"}},
    {{"timestamp": "0:30", "shot": "specific shot", "mood": "mood", "search": "search term"}},
    {{"timestamp": "1:00", "shot": "specific shot", "mood": "mood", "search": "search term"}},
    {{"timestamp": "1:30", "shot": "specific shot", "mood": "mood", "search": "search term"}},
    {{"timestamp": "2:00", "shot": "specific shot", "mood": "mood", "search": "search term"}},
    {{"timestamp": "2:30", "shot": "specific shot", "mood": "calm/resolved", "search": "search term"}},
    {{"timestamp": "3:00", "shot": "specific shot", "mood": "peaceful", "search": "search term"}}
  ],
  "voiceover_notes": "3 sentences: pace (slow, -15% rate), which specific words to pause before, where the long silences fall, overall delivery tone.",
  "titles": [
    {{"format": "A", "title": "Specific philosopher + specific emotional truth", "best": false}},
    {{"format": "B", "title": "The exact thing he feels, stated plainly", "best": true}},
    {{"format": "C", "title": "A question he has been afraid to ask", "best": false}}
  ],
  "thumbnail": {{
    "background": "dark warm description (charcoal/navy/forest green)",
    "focal_image": "one dignified focal element",
    "text_overlay": "MAX 4 WORDS ALL CAPS — emotional gut-punch, not a topic label",
    "color_palette": "dark warm base + gold #C9A84C serif text"
  }},
  "image_prompts": [
    {{"label": "01_descriptive_name", "prompt": "Cinematic 16:9. Warm, slightly desaturated. Slow, contemplative. Detailed scene description..."}},
    {{"label": "02_descriptive_name", "prompt": "..."}},
    {{"label": "03_descriptive_name", "prompt": "..."}},
    {{"label": "04_descriptive_name", "prompt": "..."}},
    {{"label": "05_descriptive_name", "prompt": "..."}},
    {{"label": "06_descriptive_name", "prompt": "..."}},
    {{"label": "07_descriptive_name", "prompt": "..."}},
    {{"label": "08_descriptive_name", "prompt": "..."}},
    {{"label": "09_descriptive_name", "prompt": "..."}},
    {{"label": "10_descriptive_name", "prompt": "..."}},
    {{"label": "11_descriptive_name", "prompt": "..."}},
    {{"label": "12_descriptive_name", "prompt": "..."}},
    {{"label": "13_descriptive_name", "prompt": "..."}},
    {{"label": "14_descriptive_name", "prompt": "..."}},
    {{"label": "15_descriptive_name", "prompt": "..."}}
  ],
  "thumbnail_configs": [
    {{
      "id": "01_main",
      "bg_image": "10_close_up_face.jpg",
      "top_text": "STOIC ELDER WISDOM",
      "main_text": "HOOK TEXT\nHERE",
      "sub_text": "MARCUS AURELIUS",
      "top_color": [201, 168, 76],
      "main_color": [201, 168, 76],
      "sub_color": [200, 190, 170]
    }},
    {{"id": "02_alt", "bg_image": "05_descriptive_name.jpg", "top_text": "STOIC ELDER WISDOM", "main_text": "HOOK TEXT\nHERE", "sub_text": "SENECA", "top_color": [201,168,76], "main_color": [201,168,76], "sub_color": [200,190,170]}},
    {{"id": "03_alt", "bg_image": "12_descriptive_name.jpg", "top_text": "STOIC ELDER WISDOM", "main_text": "HOOK TEXT\nHERE", "sub_text": "EPICTETUS", "top_color": [201,168,76], "main_color": [201,168,76], "sub_color": [200,190,170]}}
  ],
  "youtube": {{
    "title": "The best title from your 3 options above — the one a real man clicks at 11pm",
    "description": "150-200 word description. First 2 sentences mirror the hook and pull the viewer in. Third sentence states what this video gives them. Naturally weaves in: stoic wisdom, marcus aurelius, stoicism for men, {topic_keyword}, seneca, epictetus, men over 50, midlife, legacy, purpose after 50. Ends with exactly: Subscribe to StoicElderWisdom — ancient principles for men who've earned their perspective.\\n\\n📖 FREE CHAPTER — Get Chapter 5 free → stoicelderwisdom.kit.com/free-chapter\\n\\n#Stoicism #MarcusAurelius #StoicWisdom #WisdomForMen #StoicPhilosophy #MenOver50 #MidlifeWisdom #AgingWell #StoicElderWisdom #Legacy",
    "tags": ["stoicism", "marcus aurelius", "stoic wisdom", "wisdom for men", "stoic philosophy", "aging gracefully", "men over 50", "midlife wisdom", "seneca", "epictetus", "stoic elder wisdom", "legacy", "purpose after 50", "men midlife", "stoicism for men"]
  }},
  "series": "Assign to EXACTLY ONE of these 5 series — pick the best fit: Letting Go | Who Am I Now | The Long Marriage | Making Peace | What Remains",
  "pinned_comment": "One specific question that cuts to the heart of the video topic. Warm, direct, personal — like something a trusted friend would ask. Max 2 sentences. End with: Drop it below — I read every one."
}}"""


def main():
    print("Loading Gemini API key...")
    api_key = load_api_key()

    topic = get_next_topic()
    print(f"Next topic: \"{topic}\"")

    topic_keyword = topic.replace(" ", "-").lower()[:40]
    prompt = PROMPT.format(topic=topic, topic_keyword=topic_keyword)

    print("Calling Gemini to generate video package...")
    raw = call_gemini(prompt, api_key)

    print("Parsing response...")
    try:
        data = parse_json(raw)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print("Raw response (first 500 chars):")
        print(raw[:500])
        sys.exit(1)

    topic_label = data["topic"]
    print(f"\nTopic: {topic_label}")
    print(f"Hook:  {data.get('hook', '')}")

    # ── Script
    (OUTPUT_DIR / "script.txt").write_text(data["script"], encoding="utf-8")
    print(f"  Saved: output/script.txt  ({len(data['script'].split())} words)")

    # ── Image prompts
    (OUTPUT_DIR / "image_prompts.json").write_text(
        json.dumps(data["image_prompts"], indent=2), encoding="utf-8"
    )
    print(f"  Saved: output/image_prompts.json  ({len(data['image_prompts'])} prompts)")

    # ── Thumbnail configs
    (OUTPUT_DIR / "thumbnail_configs.json").write_text(
        json.dumps(data["thumbnail_configs"], indent=2), encoding="utf-8"
    )
    print(f"  Saved: output/thumbnail_configs.json")

    # ── YouTube metadata
    meta = dict(data["youtube"])
    meta["thumbnail_id"] = data["thumbnail_configs"][0]["id"]
    meta["series"]       = data.get("series", "Making Peace")
    (OUTPUT_DIR / "youtube_meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    print(f"  Saved: output/youtube_meta.json")
    print(f"  Series: {meta['series']}")

    # ── Extended production files
    overlays_txt = "\n".join(
        f"[{o['timestamp']}] {o['text']}" for o in data.get("overlays", [])
    )
    (OUTPUT_DIR / "overlays.txt").write_text(overlays_txt, encoding="utf-8")

    broll_txt = "\n".join(
        f"[{b['timestamp']}] {b['shot']} | {b['mood']} | SEARCH: {b['search']}"
        for b in data.get("broll", [])
    )
    (OUTPUT_DIR / "broll.txt").write_text(broll_txt, encoding="utf-8")
    (OUTPUT_DIR / "voiceover_notes.txt").write_text(data.get("voiceover_notes", ""), encoding="utf-8")

    titles_txt = "\n".join(
        f"{'>>> ' if t.get('best') else '    '}[{t['format']}] {t['title']}"
        for t in data.get("titles", [])
    )
    (OUTPUT_DIR / "titles.txt").write_text(titles_txt, encoding="utf-8")
    (OUTPUT_DIR / "pinned_comment.txt").write_text(data.get("pinned_comment", ""), encoding="utf-8")

    thumbnail_brief = (
        f"Background: {data['thumbnail']['background']}\n"
        f"Focal image: {data['thumbnail']['focal_image']}\n"
        f"Text overlay: {data['thumbnail']['text_overlay']}\n"
        f"Color palette: {data['thumbnail']['color_palette']}"
    )
    (OUTPUT_DIR / "thumbnail_brief.txt").write_text(thumbnail_brief, encoding="utf-8")

    save_topic(topic)
    print(f"  Updated: posted_topics.json")

    # Save hook + topic for teaser shorts pipeline
    (OUTPUT_DIR / "video_info.json").write_text(
        json.dumps({
            "topic": topic_label,
            "hook":  data.get("hook", ""),
            "title": data["youtube"]["title"],
        }, indent=2),
        encoding="utf-8",
    )
    print(f"  Saved: output/video_info.json")

    print(f"\n{'='*60}")
    print(f"  HOOK: {data.get('hook', '')}")
    print(f"\n  TITLES:")
    print(titles_txt)
    print(f"\n  THUMBNAIL: {data['thumbnail']['text_overlay']}")
    print(f"{'='*60}")
    print(f"\nScript generation complete.")


if __name__ == "__main__":
    main()
