import json
import sys
from pathlib import Path

from groq import Groq

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=config.GROQ_API_KEY)
    return _client


_SYSTEM = (
    "You are a YouTube Shorts / TikTok channel manager specializing in high-CTR spy-thriller "
    "content. You write punchy, mission-briefing-style metadata that drives clicks. "
    "Output ONLY valid JSON, no prose, no markdown fences."
)

_PROMPT = """Given this spy story, generate YouTube/TikTok metadata.

Story title concept: {title_concept}
Codename: {codename}
Hook: {hook}
Payoff (twist): {payoff}
Theme: {theme}

Return ONLY this JSON:
{{
  "titles": [
    "TITLE 1 — mission-briefing energy, all caps keywords, max 60 chars",
    "TITLE 2",
    "TITLE 3",
    "TITLE 4",
    "TITLE 5"
  ],
  "description": "2-3 sentence description that teases without spoiling. Include a CTA.",
  "hashtags": ["#hashtag1", "#hashtag2"],
  "thumbnail_caption": "ONE bold punchy line for the thumbnail, max 6 words"
}}

Rules for titles: Use formats like "CODENAME: X", "HE TRUSTED THE WRONG AGENT",
"CLASSIFIED: THE MISSION THAT NEVER EXISTED". High intrigue. 10-15 hashtags total."""


def generate_metadata(story: dict, out_dir: Path) -> dict:
    prompt = _PROMPT.format(
        title_concept=story["title_concept"],
        codename=story["codename"],
        hook=story["hook"],
        payoff=story["payoff"],
        theme=story["theme"],
    )

    resp = _get_client().chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )

    meta = json.loads(resp.choices[0].message.content)

    # Persist
    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2))

    txt_lines = [
        "=== TITLES ===",
        *[f"{i+1}. {t}" for i, t in enumerate(meta.get("titles", []))],
        "",
        "=== DESCRIPTION ===",
        meta.get("description", ""),
        "",
        "=== HASHTAGS ===",
        " ".join(meta.get("hashtags", [])),
        "",
        "=== THUMBNAIL CAPTION ===",
        meta.get("thumbnail_caption", ""),
    ]
    (out_dir / "metadata.txt").write_text("\n".join(txt_lines))

    print(f"  Metadata saved -> {out_dir}/metadata.json + metadata.txt")
    return meta
