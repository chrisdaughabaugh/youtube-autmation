import asyncio
import json
import subprocess
import sys
from pathlib import Path

import edge_tts

sys.path.insert(0, str(Path(__file__).parent.parent))
import config


def _probe_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    for stream in data.get("streams", []):
        if "duration" in stream:
            return float(stream["duration"])
    raise RuntimeError(f"Could not probe duration of {audio_path}")


async def _synthesize(text: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, config.TTS_VOICE)
    await communicate.save(str(out_path))


def generate_speech(text: str, out_path: Path) -> float:
    asyncio.run(_synthesize(text, out_path))
    return _probe_duration(out_path)


def generate_voiceover(story: dict, out_dir: Path) -> list[dict]:
    clips_dir = out_dir / "audio_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    segments = []

    # Hook
    hook_path = clips_dir / "hook.mp3"
    print(f"  TTS: hook")
    duration = generate_speech(story["hook"], hook_path)
    segments.append({
        "label": "hook",
        "text": story["hook"],
        "audio_path": str(hook_path),
        "duration": duration,
    })

    # Scenes
    for i, scene in enumerate(story["scenes"]):
        path = clips_dir / f"scene_{i:02d}.mp3"
        print(f"  TTS: scene {i}")
        duration = generate_speech(scene["narration"], path)
        segments.append({
            "label": f"scene_{i:02d}",
            "text": scene["narration"],
            "audio_path": str(path),
            "duration": duration,
            "caption": scene["caption"],
            "visual": scene["visual"],
        })

    # Payoff
    payoff_path = clips_dir / "payoff.mp3"
    print(f"  TTS: payoff")
    duration = generate_speech(story["payoff"], payoff_path)
    segments.append({
        "label": "payoff",
        "text": story["payoff"],
        "audio_path": str(payoff_path),
        "duration": duration,
    })

    # Concatenate into one narration track
    narration_path = out_dir / "narration.mp3"
    _concat_audio([s["audio_path"] for s in segments], narration_path)
    print(f"  Narration assembled -> {narration_path}")

    timing = {
        "segments": segments,
        "narration_path": str(narration_path),
        "total_duration": sum(s["duration"] for s in segments),
    }

    (out_dir / "timing.json").write_text(json.dumps(timing, indent=2))
    print(f"  Saved timing.json  total={timing['total_duration']:.1f}s")

    return segments


def _concat_audio(paths: list[str], out: Path) -> None:
    list_file = out.parent / "_concat_list.txt"
    list_file.write_text("\n".join(f"file '{p}'" for p in paths))
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    list_file.unlink(missing_ok=True)
