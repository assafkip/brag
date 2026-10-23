#!/usr/bin/env python3
"""Pace instrument: how a video moves, measured the same way every time.

  python3 pace.py <video.mp4> [--reference reference.json] [--json]

Measures, on the finished video:
  shots              scene changes found by ffmpeg scene detection at 4 fps (dissolves included)
  avg_shot_s         duration / shots
  mean_change        mean absolute grey-level change between consecutive frames, 0 to 255
  frames_moving_pct  share of frames whose change is above the threshold
  longest_still_s    the longest run of frames at or below the threshold

Definition (FPS, WIDTH, THR below) was found on 2026-10-23 by searching for the definition that
reproduces the founder's recorded results for two renders whose original instrument
(a reference-motion script from the Claudemy video project) is no longer available:
  render 1: recorded mean 3.64, moving 71%, still 2.6s  -> this gives 3.65, 72.0%, 2.60s
  render 2: recorded mean 4.18                          -> this gives 4.17
The next-best definition in that search was 25 times further off. tests/test_pace.py keeps the check.

Only numpy and ffmpeg are needed.
"""
import argparse
import json
import re
import subprocess
import sys

from pathlib import Path

import numpy as np

FPS, WIDTH, THR = 10, 160, 0.5
SCENE_FPS, SCENE_THR = 4, 0.2
TAIL_FADE_S = 1.0  # changes in the last second are the closing fade, not a shot (matches the recorded results)


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def load_gray(path, fps=FPS, width=WIDTH):
    h = int(round(width * 9 / 16))
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={width}:{h},format=gray",
           "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, width).astype(np.float32)


def motion_stats(frames, fps=FPS, thr=THR):
    d = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    moving = d > thr
    run = best = 0
    for m in moving:
        run = 0 if m else run + 1
        best = max(best, run)
    return {"mean_change": float(d.mean()), "frames_moving_pct": float(100 * moving.mean()),
            "longest_still_s": best / fps}


def shot_changes(path, scene_thr=SCENE_THR):
    vf = f"fps={SCENE_FPS},select='gt(scene,{scene_thr})',showinfo"
    p = subprocess.run(["ffmpeg", "-v", "info", "-i", path, "-vf", vf, "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(t) for t in re.findall(r"pts_time:([0-9.]+)", p.stderr)]


def measure(path):
    dur = duration(path)
    stats = motion_stats(load_gray(path))
    changes = [t for t in shot_changes(path) if t < dur - TAIL_FADE_S]
    stats.update({"duration_s": dur, "shot_changes_s": changes, "shots": len(changes) + 1,
                  "avg_shot_s": dur / (len(changes) + 1)})
    return stats


def declared_scenes(project):
    """Scene table from the project's index.html (const SCENES = [{id, start, end}, ...]), or [] if absent.

    The pixel detector above cannot see soft dissolves between pale scenes (on the Investigator Co-pilot cut,
    scene-change scores were at most 0.07 against a threshold of 0.2, so it counted one long shot). For a
    render(t) page the exact scene boundaries are in the page itself, so verify.py reads them from there and
    prints the detector's own count as information. Do not change a design to make the detector see cuts.
    """
    page = Path(project) / "index.html"
    if not page.exists():
        return []
    m = re.search(r"const\s+SCENES\s*=\s*\[(.*?)\]\s*;", page.read_text(errors="ignore"), re.S)
    if not m:
        return []
    return [(float(a), float(b)) for a, b in re.findall(r"start:\s*([0-9.]+)\s*,\s*end:\s*([0-9.]+)", m.group(1))]


def scenes_cover(scenes, dur):
    """The declared scenes must tile the video: start at 0, end near the end, no gaps, overlaps up to 1 s."""
    s = sorted(scenes)
    if not s:
        return False, "no scenes declared"
    if s[0][0] > 0.1:
        return False, f"first scene starts at {s[0][0]}s, not 0"
    if s[-1][1] < dur - 1.0:
        return False, f"last scene ends at {s[-1][1]}s, video is {dur:.1f}s"
    for (a0, a1), (b0, b1) in zip(s, s[1:]):
        if b0 > a1 + 0.05:
            return False, f"gap between {a1}s and {b0}s"
        if a1 - b0 > 1.0:
            return False, f"overlap of {a1 - b0:.1f}s at {b0}s"
    return True, ""


def compare(stats, ref):
    """Return a list of (name, value, allowed, ok) against a reference.json."""
    rows = []
    for key, lo_hi in (("avg_shot_s", ref.get("avg_shot_s_range")), ("frames_moving_pct", ref.get("frames_moving_pct_range"))):
        if lo_hi:
            v = stats[key]
            rows.append((key, v, f"{lo_hi[0]} to {lo_hi[1]}", lo_hi[0] <= v <= lo_hi[1]))
    if ref.get("longest_still_s_max") is not None:
        v = stats["longest_still_s"]
        rows.append(("longest_still_s", v, f"at most {ref['longest_still_s_max']}", v <= ref["longest_still_s_max"]))
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--reference")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    s = measure(a.video)
    rows = compare(s, json.load(open(a.reference))) if a.reference else []
    if a.json:
        print(json.dumps({"stats": s, "checks": [dict(name=n, value=v, allowed=al, ok=ok) for n, v, al, ok in rows]}, indent=2))
    else:
        print(f"duration {s['duration_s']:.1f}s | shots {s['shots']} (changes at {', '.join(f'{t:.1f}' for t in s['shot_changes_s'])}s)")
        print(f"avg shot {s['avg_shot_s']:.2f}s | mean change {s['mean_change']:.2f} | frames moving {s['frames_moving_pct']:.1f}% | longest still {s['longest_still_s']:.1f}s")
        for n, v, al, ok in rows:
            print(f"  {'PASS' if ok else 'FAIL'}  {n} = {v:.2f}  (allowed {al})")
    sys.exit(0 if all(ok for *_, ok in rows) else 1)
