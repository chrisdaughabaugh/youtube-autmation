"""
generate_thumbnail.py — StoicElderWisdom
Generates 3 thumbnail variants. Aesthetic: warm dark book cover.
- Deep charcoal / navy / forest green background
- Gold serif text (#C9A84C)
- Dignified, unhurried — like the cover of a book you'd trust
- 1280x720 (YouTube standard)
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

OUTPUT_DIR   = Path("output/thumbnails")
IMAGES_DIR   = Path("generated_images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

W, H   = 1280, 720
GOLD   = (201, 168, 76)
CREAM  = (220, 210, 190)
WHITE  = (255, 255, 255)

# Fallback thumbnail configs if output/thumbnail_configs.json not present
THUMBNAILS = [
    {
        "id":         "01_main",
        "bg_image":   "01_older_man_window_golden.jpg",
        "top_text":   "STOICELDERW ISDOM",
        "main_text":  "AT PEACE\nNOW",
        "sub_text":   "MARCUS AURELIUS",
        "top_color":  GOLD,
        "main_color": GOLD,
        "sub_color":  CREAM,
    },
    {
        "id":         "02_alt",
        "bg_image":   "07_ancient_stone_ruins_sunrise.jpg",
        "top_text":   "STOICELDERW ISDOM",
        "main_text":  "LET IT\nGO",
        "sub_text":   "SENECA",
        "top_color":  GOLD,
        "main_color": GOLD,
        "sub_color":  CREAM,
    },
    {
        "id":         "03_alt",
        "bg_image":   "12_older_man_alone_bench_park.jpg",
        "top_text":   "STOICELDERW ISDOM",
        "main_text":  "STILL\nENOUGH",
        "sub_text":   "EPICTETUS",
        "top_color":  GOLD,
        "main_color": GOLD,
        "sub_color":  CREAM,
    },
]


def load_serif_font(size: int) -> ImageFont.FreeTypeFont:
    """Load a serif font — Georgia Bold preferred, Times New Roman fallback."""
    candidates = [
        "C:/Windows/Fonts/georgiab.ttf",   # Georgia Bold
        "C:/Windows/Fonts/georgia.ttf",    # Georgia Regular
        "C:/Windows/Fonts/timesbd.ttf",    # Times New Roman Bold
        "C:/Windows/Fonts/times.ttf",      # Times New Roman
        "C:/Windows/Fonts/cambriab.ttf",   # Cambria Bold
        "C:/Windows/Fonts/cambria.ttf",
        "C:/Windows/Fonts/arialbd.ttf",    # Last resort
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def load_sans_font(size: int) -> ImageFont.FreeTypeFont:
    """Small sans for channel name label."""
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def apply_warm_dark_overlay(img: Image.Image) -> Image.Image:
    """Darken the image and add a warm dark vignette suitable for text overlay."""
    img = img.convert("RGB")

    # Desaturate slightly for that warm film look
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(0.80)

    # Darken overall — keep enough brightness so the image reads on mobile
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(0.68)

    # Warm dark gradient from left (where text lives)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    # Heavy dark band on the left half for text legibility
    for i in range(img.width // 2 + 100):
        alpha = int(200 * (1 - i / (img.width // 2 + 100)))
        draw.rectangle([i, 0, i + 1, img.height], fill=(10, 5, 0, alpha))

    # Dark bottom strip
    for i in range(img.height // 4):
        alpha = int(160 * (1 - i / (img.height // 4)))
        y = img.height - i
        draw.rectangle([0, y, img.width, y + 1], fill=(10, 5, 0, alpha))

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def draw_text_with_stroke(
    draw: ImageDraw.ImageDraw,
    xy: tuple,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    stroke_width: int = 3,
    align: str = "left",
) -> None:
    x, y = xy
    sw = stroke_width
    for dx in range(-sw, sw + 1):
        for dy in range(-sw, sw + 1):
            if dx != 0 or dy != 0:
                draw.multiline_text((x + dx, y + dy), text, font=font,
                                    fill=(0, 0, 0), align=align)
    draw.multiline_text((x, y), text, font=font, fill=fill, align=align)


def make_thumbnail(cfg: dict) -> None:
    bg_path = IMAGES_DIR / cfg["bg_image"]

    if not bg_path.exists():
        available = sorted(IMAGES_DIR.glob("*.jpg"))
        if not available:
            print(f"  No images found - skipping {cfg['id']}")
            return
        bg_path = available[0]
        print(f"  bg image missing, using fallback: {bg_path.name}")

    # ── Load & crop to 1280x720 ────────────────────────────────────────────────
    img = Image.open(bg_path).convert("RGB")
    img_ratio    = img.width / img.height
    target_ratio = W / H
    if img_ratio > target_ratio:
        new_h = H
        new_w = int(img.width * H / img.height)
    else:
        new_w = W
        new_h = int(img.height * W / img.width)
    img  = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - W) // 2
    top  = (new_h - H) // 2
    img  = img.crop((left, top, left + W, top + H))

    # ── Brighten image overall — let the scene breathe ─────────────────────────
    img = ImageEnhance.Color(img).enhance(0.85)
    img = ImageEnhance.Brightness(img).enhance(0.75)
    img = img.convert("RGBA")

    # ── Split-panel overlay: solid dark LEFT panel, fade to transparent RIGHT ──
    # Left 52% = solid dark (text lives here), right side = image shows through
    panel_w   = int(W * 0.58)
    panel     = Image.new("RGBA", img.size, (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel)

    # Solid dark block covering left panel
    panel_draw.rectangle([0, 0, panel_w, H], fill=(12, 8, 4, 235))

    # Soft gradient fade from panel edge to transparent (blend zone)
    fade_w = 140
    for i in range(fade_w):
        alpha = int(235 * (1 - i / fade_w))
        panel_draw.rectangle([panel_w + i, 0, panel_w + i + 1, H],
                              fill=(12, 8, 4, alpha))

    # Dark strip at very bottom across full width (holds philosopher name)
    for i in range(90):
        alpha = int(210 * (1 - i / 90))
        y = H - i
        panel_draw.rectangle([0, y, W, y + 1], fill=(8, 5, 2, alpha))

    img = Image.alpha_composite(img, panel).convert("RGB")

    # ── Gold accent stripe on left edge ───────────────────────────────────────
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 7, H], fill=tuple(cfg["top_color"]))

    # ── Fonts ──────────────────────────────────────────────────────────────────
    font_top  = load_sans_font(28)
    font_main = load_serif_font(128)
    font_sub  = load_serif_font(40)

    x = 28   # left margin (after gold stripe)

    # Channel name — gold, small caps feel
    draw_text_with_stroke(draw, (x, 38), cfg["top_text"],
                          font_top, tuple(cfg["top_color"]), stroke_width=2)

    # Thin gold rule under channel name
    draw.rectangle([x, 76, x + 320, 79], fill=tuple(cfg["top_color"]))

    # MAIN TEXT — large white serif, maximum impact
    draw_text_with_stroke(draw, (x, 92), cfg["main_text"],
                          font_main, (255, 255, 255), stroke_width=6)

    # Philosopher name — gold, bottom left
    draw_text_with_stroke(draw, (x, H - 70), cfg["sub_text"],
                          font_sub, tuple(cfg["top_color"]), stroke_width=2)

    # ── Thin gold border frame around entire thumbnail ─────────────────────────
    draw.rectangle([0, 0, W - 1, H - 1], outline=tuple(cfg["top_color"]), width=3)

    out_path = OUTPUT_DIR / f"{cfg['id']}.jpg"
    img.save(out_path, "JPEG", quality=95)
    print(f"  Saved: {out_path}")


def main():
    thumbnails = THUMBNAILS
    cfg_file   = Path("output/thumbnail_configs.json")
    if cfg_file.exists():
        raw        = json.loads(cfg_file.read_text(encoding="utf-8"))
        thumbnails = [
            {**t,
             "top_color":  tuple(t["top_color"]),
             "main_color": tuple(t["main_color"]),
             "sub_color":  tuple(t["sub_color"])}
            for t in raw
        ]
        print(f"Loaded {len(thumbnails)} thumbnail configs from output/thumbnail_configs.json")

    print(f"Generating {len(thumbnails)} thumbnails -> {OUTPUT_DIR}/\n")
    for cfg in thumbnails:
        print(f"Thumbnail: {cfg['id']}")
        make_thumbnail(cfg)
    print("\nDone.")


if __name__ == "__main__":
    main()
