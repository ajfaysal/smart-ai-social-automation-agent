"""Built-in original/procedural mood music library.
No third-party recordings are bundled, so the generated underscore has no
external music license or Content-ID ownership dependency.
"""
from pathlib import Path
import subprocess

MOODS = {
    "neutral": (72, 220.00), "happy": (104, 261.63), "laughing": (118, 293.66),
    "sad": (58, 196.00), "crying": (52, 174.61), "angry": (96, 146.83),
    "scared": (78, 164.81), "surprised": (112, 246.94), "romantic": (66, 220.00),
    "whispering": (54, 207.65), "shouting": (100, 130.81), "apologetic": (62, 196.00),
}


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr[-2000:] or "audio generation failed")


def generate_mood_track(mood: str, duration: float, out_path: Path):
    bpm, root = MOODS.get(mood, MOODS["neutral"])
    duration = max(1.0, float(duration))
    beat = 60.0 / bpm
    freqs = [root, root * 1.25, root * 1.5, root / 2]
    inputs = []
    for i, freq in enumerate(freqs):
        amp = [0.045, 0.022, 0.018, 0.025][i]
        inputs.append(f"aevalsrc={amp}*sin(2*PI*{freq:.3f}*t)*(0.72+0.28*sin(2*PI*0.11*t)):s=48000:d={duration:.3f}")
    inputs.append(f"aevalsrc=0.012*sin(2*PI*{root/2:.3f}*t)*max(0,sin(2*PI*{1/beat:.5f}*t)):s=48000:d={duration:.3f}")
    cmd = ["ffmpeg", "-y"]
    for src in inputs:
        cmd += ["-f", "lavfi", "-i", src]
    labels = "".join(f"[{i}:a]" for i in range(len(inputs)))
    filt = labels + f"amix=inputs={len(inputs)}:duration=longest:normalize=0,afade=t=in:d=0.6,afade=t=out:st={max(0,duration-0.8):.3f}:d=0.8,volume=0.75"
    cmd += ["-filter_complex", filt, "-ar", "48000", "-ac", "2", "-t", f"{duration:.3f}", "-c:a", "pcm_s16le", str(out_path)]
    _run(cmd)
    return out_path


def choose_mood(emotions):
    counts = {m: 0 for m in MOODS}
    for emotion in emotions:
        key = str(emotion or "neutral").lower()
        counts[key if key in counts else "neutral"] += 1
    return max(counts, key=counts.get) if counts else "neutral"


def library_info():
    return {
        "type": "original_procedural",
        "license": "No third-party recording bundled; generated locally by the application",
        "moods": sorted(MOODS),
        "attribution_required": False,
    }
