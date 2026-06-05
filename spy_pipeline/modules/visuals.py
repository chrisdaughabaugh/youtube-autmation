import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

W = config.VIDEO_WIDTH    # 1080
H = config.VIDEO_HEIGHT   # 1920

# Palette
BG_TOP    = (5, 10, 25)
BG_BOT    = (10, 20, 45)
STICK_COL = (210, 220, 235)
ACCENT    = (80, 140, 220)
SHADOW    = (0, 0, 0, 120)

POSE_KEYWORDS = {
    "running":   ["run", "sprint", "flee", "chase", "escape", "bolt"],
    "handoff":   ["handoff", "exchange", "briefcase pass", "hand", "transfer", "pass"],
    "standoff":  ["standoff", "confront", "face", "aim", "gun", "weapon", "point"],
    "shadow":    ["shadow", "silhouette", "lurk", "watch", "observe", "surveillance"],
    "car":       ["car", "vehicle", "drive", "street", "road", "alley"],
    "seated":    ["sit", "seated", "desk", "table", "debrief", "meeting", "wait"],
    "suited":    ["suited", "briefcase", "dead drop", "standing", "operative", "agent"],
}


def _match_pose(visual_desc: str) -> str:
    desc = visual_desc.lower()
    for pose, kws in POSE_KEYWORDS.items():
        if any(kw in desc for kw in kws):
            return pose
    return "suited"


def _gradient_bg(draw: ImageDraw.Draw) -> None:
    for y in range(H):
        t = y / H
        r = int(BG_TOP[0] + (BG_BOT[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOT[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOT[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def _accent_lines(draw: ImageDraw.Draw) -> None:
    for i in range(3):
        y = H // 4 + i * H // 4
        draw.line([(0, y), (W, y)], fill=(30, 50, 90), width=1)


def _shadow_ellipse(draw: ImageDraw.Draw, cx: int, cy: int, rx: int, ry: int) -> None:
    draw.ellipse(
        [cx - rx, cy - ry, cx + rx, cy + ry],
        fill=(0, 0, 0, 60),
    )


def _stick_figure(draw: ImageDraw.Draw, cx: int, cy: int, scale: float = 1.0,
                  color: tuple = STICK_COL, lw: int = 8) -> None:
    s = scale
    head_r = int(45 * s)
    body_len = int(160 * s)
    arm_len = int(110 * s)
    leg_len = int(130 * s)

    # Ground shadow
    _shadow_ellipse(draw, cx, cy + body_len + leg_len + head_r + 10,
                    int(80 * s), int(20 * s))

    # Head
    hy = cy - head_r
    draw.ellipse([cx - head_r, hy - head_r, cx + head_r, hy + head_r],
                 outline=color, width=lw)

    # Body
    neck = hy + head_r
    waist = neck + body_len
    draw.line([cx, neck, cx, waist], fill=color, width=lw)

    # Arms
    shoulder = neck + int(50 * s)
    draw.line([cx, shoulder, cx - arm_len, shoulder + int(60 * s)], fill=color, width=lw)
    draw.line([cx, shoulder, cx + arm_len, shoulder + int(60 * s)], fill=color, width=lw)

    # Legs
    draw.line([cx, waist, cx - int(70 * s), waist + leg_len], fill=color, width=lw)
    draw.line([cx, waist, cx + int(70 * s), waist + leg_len], fill=color, width=lw)


def _briefcase(draw: ImageDraw.Draw, x: int, y: int, scale: float = 1.0,
               color: tuple = STICK_COL) -> None:
    s = scale
    w, h = int(80 * s), int(55 * s)
    draw.rectangle([x, y, x + w, y + h], outline=color, width=5)
    draw.line([x + w // 4, y, x + w // 4, y - int(20 * s)], fill=color, width=5)
    draw.line([x + 3 * w // 4, y, x + 3 * w // 4, y - int(20 * s)], fill=color, width=5)
    draw.line([x + w // 4, y - int(20 * s), x + 3 * w // 4, y - int(20 * s)],
              fill=color, width=5)


def _draw_suited(draw: ImageDraw.Draw) -> None:
    cx, cy = W // 2, H // 2 - 100
    _stick_figure(draw, cx, cy)
    arm_end_x = cx + int(110 * 1.0)
    arm_end_y = cy - 45 + 50 + 60  # shoulder y + arm drop
    _briefcase(draw, arm_end_x, arm_end_y)


def _draw_handoff(draw: ImageDraw.Draw) -> None:
    # Two figures facing each other
    cy = H // 2 - 50
    _stick_figure(draw, W // 3, cy, scale=0.85)
    _stick_figure(draw, 2 * W // 3, cy, scale=0.85)
    mid_x = W // 2
    bx = mid_x - 40
    by = cy + 120
    _briefcase(draw, bx, by, scale=0.9, color=ACCENT)
    # connecting line (the pass)
    draw.line([W // 3 + 90, cy + 150, 2 * W // 3 - 90, cy + 150],
              fill=ACCENT, width=4)


def _draw_running(draw: ImageDraw.Draw) -> None:
    cx, cy = W // 2, H // 2 - 80
    s = 1.1
    head_r = int(45 * s)
    body_len = int(160 * s)
    arm_len = int(110 * s)
    leg_len = int(130 * s)
    lw = 9
    _shadow_ellipse(draw, cx, cy + body_len + leg_len + head_r + 10,
                    int(90 * s), int(22 * s))
    hy = cy - head_r
    draw.ellipse([cx - head_r, hy - head_r, cx + head_r, hy + head_r],
                 outline=STICK_COL, width=lw)
    neck = hy + head_r
    waist = neck + body_len
    draw.line([cx, neck, cx - 20, waist], fill=STICK_COL, width=lw)
    shoulder = neck + int(50 * s)
    draw.line([cx - 20, shoulder, cx - 20 - arm_len, shoulder - int(50 * s)],
              fill=STICK_COL, width=lw)
    draw.line([cx - 20, shoulder, cx - 20 + arm_len, shoulder + int(80 * s)],
              fill=STICK_COL, width=lw)
    draw.line([cx - 20, waist, cx - 20 - int(90 * s), waist + leg_len],
              fill=STICK_COL, width=lw)
    draw.line([cx - 20, waist, cx - 20 + int(50 * s), waist + int(80 * s)],
              fill=STICK_COL, width=lw)
    # motion lines
    for i in range(4):
        draw.line([cx - 20 - 140 - i * 30, shoulder + i * 40,
                   cx - 20 - 180 - i * 30, shoulder + i * 40],
                  fill=ACCENT, width=3)


def _draw_shadow(draw: ImageDraw.Draw) -> None:
    cx, cy = W // 2, H // 2 - 50
    # Dark silhouette
    s = 1.15
    head_r = int(45 * s)
    body_len = int(160 * s)
    arm_len = int(110 * s)
    leg_len = int(130 * s)
    lw = 12
    col = (60, 70, 90)
    hy = cy - head_r
    draw.ellipse([cx - head_r, hy - head_r, cx + head_r, hy + head_r],
                 fill=col, outline=col, width=lw)
    neck = hy + head_r
    waist = neck + body_len
    draw.line([cx, neck, cx, waist], fill=col, width=lw + 4)
    shoulder = neck + int(50 * s)
    draw.line([cx, shoulder, cx - arm_len, shoulder + int(60 * s)], fill=col, width=lw)
    draw.line([cx, shoulder, cx + arm_len, shoulder + int(60 * s)], fill=col, width=lw)
    draw.line([cx, waist, cx - int(70 * s), waist + leg_len], fill=col, width=lw)
    draw.line([cx, waist, cx + int(70 * s), waist + leg_len], fill=col, width=lw)
    # spotlight effect
    for r in range(200, 0, -40):
        alpha = max(20, 80 - r // 3)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=(120, 160, 255, alpha), width=2)


def _draw_car(draw: ImageDraw.Draw) -> None:
    # Simple car silhouette
    bx, by = W // 2 - 220, H // 2 + 80
    bw, bh = 440, 120
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=30,
                            fill=(30, 40, 70), outline=ACCENT, width=4)
    # roof
    draw.polygon([
        (bx + 80, by), (bx + bw - 80, by),
        (bx + bw - 120, by - 80), (bx + 120, by - 80),
    ], fill=(20, 30, 55), outline=ACCENT)
    # wheels
    for wx in [bx + 70, bx + bw - 70]:
        wy = by + bh
        draw.ellipse([wx - 45, wy - 45, wx + 45, wy + 45],
                     fill=(15, 20, 40), outline=STICK_COL, width=5)
    # headlights
    draw.line([bx + bw, by + 30, bx + bw + 60, by + 20], fill=(200, 200, 100), width=5)
    _stick_figure(draw, W // 2 - 150, H // 2 - 150, scale=0.75)


def _draw_standoff(draw: ImageDraw.Draw) -> None:
    cy = H // 2 - 60
    # Two figures facing each other with arms extended
    _stick_figure(draw, W // 3 - 20, cy, scale=0.9, color=(210, 220, 235))
    _stick_figure(draw, 2 * W // 3 + 20, cy, scale=0.9, color=(160, 80, 80))
    # arms extended toward each other (tension, no gun drawn explicitly)
    draw.line([W // 3 + 80, cy + 90, W // 2 - 40, cy + 90],
              fill=ACCENT, width=5)
    draw.line([2 * W // 3 - 80, cy + 90, W // 2 + 40, cy + 90],
              fill=(160, 80, 80), width=5)
    # tension line between them
    for i in range(5):
        x = W // 2 - 20 + i * 8
        draw.line([x, cy + 80, x, cy + 100], fill=(200, 180, 50), width=2)


def _draw_seated(draw: ImageDraw.Draw) -> None:
    cx, cy = W // 2, H // 2 - 20
    s = 1.0
    head_r = int(45 * s)
    lw = 8
    hy = cy - head_r
    draw.ellipse([cx - head_r, hy - head_r, cx + head_r, hy + head_r],
                 outline=STICK_COL, width=lw)
    neck = hy + head_r
    torso_end = neck + int(130 * s)
    draw.line([cx, neck, cx, torso_end], fill=STICK_COL, width=lw)
    shoulder = neck + int(50 * s)
    draw.line([cx, shoulder, cx - int(110 * s), shoulder + int(60 * s)],
              fill=STICK_COL, width=lw)
    draw.line([cx, shoulder, cx + int(110 * s), shoulder + int(60 * s)],
              fill=STICK_COL, width=lw)
    draw.line([cx, torso_end, cx - int(80 * s), torso_end + int(10 * s)],
              fill=STICK_COL, width=lw)
    draw.line([cx, torso_end, cx + int(80 * s), torso_end + int(10 * s)],
              fill=STICK_COL, width=lw)
    # desk
    desk_y = torso_end + 15
    draw.rectangle([cx - 200, desk_y, cx + 200, desk_y + 15], fill=ACCENT)
    draw.rectangle([cx - 180, desk_y + 15, cx - 160, desk_y + 60], fill=ACCENT)
    draw.rectangle([cx + 160, desk_y + 15, cx + 180, desk_y + 60], fill=ACCENT)


_POSE_DRAWERS = {
    "suited":   _draw_suited,
    "handoff":  _draw_handoff,
    "running":  _draw_running,
    "shadow":   _draw_shadow,
    "car":      _draw_car,
    "standoff": _draw_standoff,
    "seated":   _draw_seated,
}


def render_scene(visual_desc: str, out_path: Path) -> None:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img, "RGBA")
    _gradient_bg(draw)
    _accent_lines(draw)
    pose = _match_pose(visual_desc)
    _POSE_DRAWERS[pose](draw)
    img.save(out_path, "PNG")


def generate_visuals(story: dict, out_dir: Path) -> list[Path]:
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    paths = []

    # Hook frame
    hook_path = frames_dir / "hook.png"
    render_scene("shadow silhouette surveillance", hook_path)
    paths.append(hook_path)
    print(f"  Frame: hook.png")

    # Scene frames
    for i, scene in enumerate(story["scenes"]):
        path = frames_dir / f"scene_{i:02d}.png"
        render_scene(scene["visual"], path)
        paths.append(path)
        print(f"  Frame: scene_{i:02d}.png  [{_match_pose(scene['visual'])}]")

    # Payoff frame
    payoff_path = frames_dir / "payoff.png"
    render_scene("shadow silhouette reveal", payoff_path)
    paths.append(payoff_path)
    print(f"  Frame: payoff.png")

    return paths
