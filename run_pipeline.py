"""
run_pipeline.py — StoicElderWisdom
Full automation pipeline: script → images → voiceover → video →
subtitles → Short clip → thumbnails → upload main → upload Short.
"""
import json
import os
import subprocess
import sys
import io

# Force UTF-8 stdout so em-dashes, arrows, and emoji in print() don't crash on Windows
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import time
import shutil
import threading
from pathlib import Path

SCRIPTS = [
    ("1/9 — Generating script (AI)",   "generate_script.py"),
    ("2/9 — Generating images",        "generate_images.py"),
    ("3/9 — Generating voiceover",     "generate_voiceover.py"),
    ("4/9 — Assembling video",         "assemble_video.py"),
    ("5/9 — Generating subtitles",     "generate_subtitles.py"),
    ("6/9 — Generating Short clip",    "generate_short.py"),
    ("7/9 — Generating thumbnails",    "generate_thumbnail.py"),
    ("8/9 — Uploading main video",     "upload_to_youtube.py"),
    ("9/9 — Uploading Short",          "upload_short.py"),
]


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


def cleanup() -> None:
    print("Cleaning up previous run...")
    for d in ["generated_images", "output"]:
        p = Path(d)
        if p.exists():
            shutil.rmtree(p)
        p.mkdir()
    (Path("output") / "thumbnails").mkdir()
    print("  Clean.\n")


def run_step(label: str, script: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    tg(f"⚙️ <b>{label}</b>")
    start  = time.time()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    result = subprocess.run([sys.executable, script], env=env)
    elapsed = time.time() - start
    if result.returncode != 0:
        print(f"\nERROR: {script} failed. Pipeline stopped.")
        tg(f"❌ StoicElderWisdom pipeline failed at: <b>{label}</b>")
        sys.exit(1)
    print(f"  Done in {elapsed:.0f}s")


def main():
    print("\nSTOICELDERWISDOM PIPELINE — STARTING")
    print(f"Steps: {len(SCRIPTS)}")
    total_start = time.time()
    tg("🚀 <b>StoicElderWisdom Pipeline starting!</b>")

    cleanup()

    for label, script in SCRIPTS:
        if not Path(script).exists():
            print(f"ERROR: {script} not found.")
            tg(f"❌ Script not found: <code>{script}</code>")
            sys.exit(1)
        run_step(label, script)

    total = time.time() - total_start

    yt_url = ""
    try:
        meta   = json.loads(Path("output/video_meta.json").read_text())
        vid_id = meta.get("video_id", "")
        title  = meta.get("title", "")
        if vid_id:
            yt_url = f"https://www.youtube.com/watch?v={vid_id}"
    except Exception:
        pass

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE in {total/60:.1f} minutes")
    if yt_url:
        print(f"  Live: {yt_url}")
    print(f"  Video and Short are live on YouTube.")
    print(f"{'='*60}\n")

    done_msg = (
        f"✅ <b>StoicElderWisdom complete in {total/60:.1f} min!</b>\n\n"
        f"🎬 <a href='{yt_url}'>{title}</a>" if yt_url else
        f"✅ <b>StoicElderWisdom complete in {total/60:.1f} min!</b>"
    )
    tg(done_msg)


if __name__ == "__main__":
    main()
