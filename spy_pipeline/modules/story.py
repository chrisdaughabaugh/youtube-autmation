import json
import random
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


def _random_theme() -> str:
    topics = [t.strip() for t in config.TOPICS_PATH.read_text().splitlines() if t.strip()]
    return random.choice(topics)


_SYSTEM = (
    "You are a master short-form thriller writer for a faceless animated SPY channel. "
    "You write ONLY original espionage micro-stories using fictional agents, codenames, "
    "and agencies. Never reference real franchises, real people, or real intelligence "
    "services. All violence is stylized and cartoonish — never graphic. "
    "You output ONLY valid JSON, no prose, no markdown fences."
)

_PROMPT_TEMPLATE = """Write ONE original espionage micro-story for a 60-90 second vertical video.

Rules:
- ONLY fictional agents, codenames, and agencies (e.g. "The Division", "Sector 9")
- 3-second HOOK that drops us mid-crisis and opens a loop
- Rising stakes with a ticking-clock feel
- A midpoint complication that raises the cost of failure
- A sharp TWIST or reveal at the very end (betrayal, double identity, setup, sacrifice)
- Tight, cinematic, specific — concrete details, real stakes
- NO clichés like "little did they know", "suddenly", or "it was too late"
- Narration sounds tense and natural when read aloud
- 6 to 10 scenes total
- Theme: {THEME}

Return ONLY this exact JSON structure (no fences, no extra keys):
{{
  "title_concept": "short punchy title concept",
  "codename": "the operative or mission codename",
  "hook": "first spoken line — drops us mid-crisis, opens a loop",
  "scenes": [
    {{
      "narration": "one or two tense spoken sentences",
      "caption": "short punchy on-screen text, max 8 words",
      "visual": "simple stick-figure scene description, e.g. suited figure at a dead drop in shadow"
    }}
  ],
  "payoff": "the final twist line that lands hard",
  "theme": "{THEME}"
}}"""


def _call_groq(theme: str) -> dict:
    prompt = _PROMPT_TEMPLATE.format(THEME=theme)
    resp = _get_client().chat.completions.create(
        model=config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ],
        temperature=0.9,
        max_tokens=2048,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content
    return json.loads(raw)


def _validate(story: dict) -> None:
    required = {"title_concept", "codename", "hook", "scenes", "payoff", "theme"}
    missing = required - set(story.keys())
    if missing:
        raise ValueError(f"Story JSON missing keys: {missing}")
    if not isinstance(story["scenes"], list) or len(story["scenes"]) < 4:
        raise ValueError("Story must have at least 4 scenes")
    for i, scene in enumerate(story["scenes"]):
        for key in ("narration", "caption", "visual"):
            if not scene.get(key):
                raise ValueError(f"Scene {i} missing '{key}'")


def generate_story(theme: str | None = None, out_dir: Path | None = None) -> dict:
    theme = theme or _random_theme()
    print(f"  Generating story — theme: '{theme}'")

    story = None
    last_err = None
    for attempt in range(2):
        try:
            story = _call_groq(theme)
            _validate(story)
            break
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
            print(f"  Attempt {attempt + 1} failed validation: {e}. Retrying...")

    if story is None:
        raise RuntimeError(f"Story generation failed after 2 attempts: {last_err}")

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "story.json").write_text(json.dumps(story, indent=2))
        print(f"  Saved story.json -> {out_dir}")

    return story


if __name__ == "__main__":
    import sys
    theme_arg = sys.argv[1] if len(sys.argv) > 1 else None
    result = generate_story(theme_arg)
    print(json.dumps(result, indent=2))
