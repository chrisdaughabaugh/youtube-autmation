#!/usr/bin/env python3
"""
Spy-Thriller Video Pipeline — CLI entry point

Usage:
  python main.py single [--theme "the mole"]
  python main.py batch  [--count 5]
  python main.py stage story   [--theme "..."]
  python main.py stage visuals --dir <output_folder>
  python main.py stage assemble --dir <output_folder>
  python main.py stage metadata --dir <output_folder>
"""

import argparse
import json
import random
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from modules.story import generate_story
from modules.visuals import generate_visuals
from modules.assemble import assemble_video
from modules.metadata import generate_metadata


def _new_output_dir(theme: str) -> Path:
    slug = theme.replace(" ", "_").replace("/", "-")[:30]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = config.OUTPUT_PATH / f"{ts}_{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def run_single(theme: str | None = None, out_dir: Path | None = None) -> Path:
    if theme is None:
        topics = [t.strip() for t in config.TOPICS_PATH.read_text().splitlines() if t.strip()]
        theme = random.choice(topics)

    out_dir = out_dir or _new_output_dir(theme)
    print(f"\n{'='*60}")
    print(f"  SPY PIPELINE  |  theme: {theme}")
    print(f"  Output: {out_dir}")
    print(f"{'='*60}\n")

    print("[1/4] Generating story...")
    story = generate_story(theme, out_dir)
    print(f"      Codename: {story['codename']}")

    print("[2/4] Rendering frames...")
    frame_paths = generate_visuals(story, out_dir)
    print(f"      {len(frame_paths)} frames rendered")

    print("[3/4] Assembling video...")
    video_path = assemble_video(story, frame_paths, out_dir)

    print("[4/4] Generating metadata...")
    meta = generate_metadata(story, out_dir)
    print(f"      Title 1: {meta['titles'][0]}")

    print(f"\n  Done! -> {video_path}\n")
    return video_path


def run_batch(count: int) -> None:
    topics = [t.strip() for t in config.TOPICS_PATH.read_text().splitlines() if t.strip()]
    random.shuffle(topics)
    themes = (topics * ((count // len(topics)) + 1))[:count]

    print(f"\n  BATCH MODE — producing {count} videos\n")
    success, failed = 0, 0

    for i, theme in enumerate(themes, 1):
        print(f"\n--- Batch {i}/{count}: {theme} ---")
        try:
            run_single(theme)
            success += 1
        except Exception as e:
            failed += 1
            print(f"  ERROR on '{theme}': {e}")
            log_path = config.OUTPUT_PATH / "batch_errors.log"
            with open(log_path, "a") as f:
                f.write(f"\n[{datetime.now()}] theme={theme}\n")
                traceback.print_exc(file=f)
            print(f"  Logged to {log_path}. Continuing...")

    print(f"\n  Batch complete: {success} succeeded, {failed} failed.")


def run_stage(stage: str, theme: str | None, dir_path: str | None) -> None:
    if stage == "story":
        out = _new_output_dir(theme or "random") if not dir_path else Path(dir_path)
        story = generate_story(theme, out)
        print(json.dumps(story, indent=2))

    elif stage == "visuals":
        if not dir_path:
            sys.exit("  --dir required for stage visuals")
        out = Path(dir_path)
        story = json.loads((out / "story.json").read_text())
        for p in generate_visuals(story, out):
            print(p)

    elif stage == "assemble":
        if not dir_path:
            sys.exit("  --dir required for stage assemble")
        out = Path(dir_path)
        story = json.loads((out / "story.json").read_text())
        frame_paths = sorted((out / "frames").glob("*.png"))
        assemble_video(story, frame_paths, out)

    elif stage == "metadata":
        if not dir_path:
            sys.exit("  --dir required for stage metadata")
        out = Path(dir_path)
        story = json.loads((out / "story.json").read_text())
        print(json.dumps(generate_metadata(story, out), indent=2))

    else:
        sys.exit(f"  Unknown stage: {stage}. Choose: story, visuals, assemble, metadata")


def main():
    parser = argparse.ArgumentParser(
        description="Spy-Thriller Video Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    p_single = sub.add_parser("single", help="Produce one video end-to-end")
    p_single.add_argument("--theme", help="Spy theme (omit to pick randomly)")

    p_batch = sub.add_parser("batch", help="Produce N videos")
    p_batch.add_argument("--count", type=int, default=config.BATCH_SIZE)

    p_stage = sub.add_parser("stage", help="Run a single pipeline stage")
    p_stage.add_argument("name", help="story | visuals | assemble | metadata")
    p_stage.add_argument("--theme", help="Theme (story stage only)")
    p_stage.add_argument("--dir", dest="dir_path", help="Output folder (required for most stages)")

    args = parser.parse_args()

    if args.command == "single":
        try:
            run_single(args.theme)
        except Exception as e:
            print(f"\n  Pipeline error: {e}")
            sys.exit(1)

    elif args.command == "batch":
        try:
            run_batch(args.count)
        except Exception as e:
            print(f"\n  Batch error: {e}")
            sys.exit(1)

    elif args.command == "stage":
        try:
            run_stage(args.name, getattr(args, "theme", None), getattr(args, "dir_path", None))
        except Exception as e:
            print(f"\n  Stage error: {e}")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
