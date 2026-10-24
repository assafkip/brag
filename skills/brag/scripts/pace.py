#!/usr/bin/env python3
"""Pace instrument: how a video moves, measured the same way every time.

  python3 pace.py <video.mp4> [--reference reference.json] [--json]

Measures, on the finished video:
  shots              scene changes found by ffmpeg scene detection at 4 fps (dissolves included)
  avg_shot_s         duration / shots
  mean_change        mean absolute grey-level change between consecutive frames, 0 to 255
  frames_moving_pct  share of frames whose whole-frame mean change is above the threshold
  longest_still_s    the longest run of frames at or below that threshold
  tile_change_max    the largest per-tile mean change seen in the video (the small-area instrument)
  area_moving_pct    share of frames whose busiest tile changed above TILE_THR
  longest_area_still_s  the longest run of frames whose busiest tile was at or below TILE_THR

The whole-frame mean is reported and is NOT what compare() gates: a mean over the whole frame
divides a small element's motion by the whole page, so in-place UI motion on a white plane reads
as a still (ASK-3036). compare() gates the per-tile numbers; verify.py prints the mean as INFO.

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
TILE_COLS, TILE_ROWS, TILE_THR = 16, 9, 2.0
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


def longest_still_s(moving, fps=FPS):
    """Seconds in the longest unbroken run of frames that did NOT move."""
    run = best = 0
    for m in moving:
        run = 0 if m else run + 1
        best = max(best, run)
    return best / fps


def tile_max_change(frames, cols=TILE_COLS, rows=TILE_ROWS):
    """Per frame pair, the largest mean grey change inside any one tile.

    Why a tile and not the whole frame: a whole-frame mean divides a small element's motion by
    the whole page, so chips popping and rows sliding on a white plane came out at 8 percent
    moving with a 9.3 s longest still, and verify reported pace FAIL on the openwitness cut the
    founder had approved (ASK-3036). A tile divides by the tile's own area, so in-place motion
    registers. The frame is cropped to whole tiles; a remainder of at most cols-1 by rows-1
    pixels at the right and bottom edge is dropped.
    """
    d = np.abs(np.diff(frames, axis=0))
    n, h, w = d.shape
    th, tw = h // rows, w // cols
    d = d[:, :th * rows, :tw * cols]
    tiles = d.reshape(n, rows, th, cols, tw).mean(axis=(2, 4))
    return tiles.reshape(n, -1).max(axis=1)


def motion_stats(frames, fps=FPS, thr=THR, tile_thr=TILE_THR):
    d = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    moving = d > thr
    tiles = tile_max_change(frames)
    area_moving = tiles > tile_thr
    return {"mean_change": float(d.mean()), "frames_moving_pct": float(100 * moving.mean()),
            "longest_still_s": longest_still_s(moving, fps),
            "tile_change_max": float(tiles.max()), "tile_change_mean": float(tiles.mean()),
            "area_moving_pct": float(100 * area_moving.mean()),
            "longest_area_still_s": longest_still_s(area_moving, fps)}


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

    The pixel detector above cannot see soft dissolves between pale scenes (on a product explainer cut,
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
    """Return a list of (name, value, allowed, ok) against a reference.json.

    The motion rows read the per-tile instrument while keeping the reference.json key names
    (frames_moving_pct_range, longest_still_s_max): the keys are the founder's done-means and
    every project on disk carries them, so the instrument behind them changed and the ranges
    did not. A scrolling reference reads at least as high on tiles as on the whole frame, so
    the recorded floor still holds; the whole-frame numbers are reported, never gated.
    """
    rows = []
    lo_hi = ref.get("avg_shot_s_range")
    if lo_hi:
        v = stats["avg_shot_s"]
        rows.append(("avg_shot_s", v, f"{lo_hi[0]} to {lo_hi[1]}", lo_hi[0] <= v <= lo_hi[1]))
    lo_hi = ref.get("frames_moving_pct_range")
    if lo_hi:
        v = stats["area_moving_pct"]
        rows.append(("area_moving_pct", v, f"{lo_hi[0]} to {lo_hi[1]}", lo_hi[0] <= v <= lo_hi[1]))
    if ref.get("longest_still_s_max") is not None:
        v = stats["longest_area_still_s"]
        rows.append(("longest_area_still_s", v, f"at most {ref['longest_still_s_max']}", v <= ref["longest_still_s_max"]))
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
        print(f"avg shot {s['avg_shot_s']:.2f}s | tile change max {s['tile_change_max']:.2f} | area moving {s['area_moving_pct']:.1f}%"
              f" | longest area still {s['longest_area_still_s']:.1f}s")
        print(f"  whole-frame mean change {s['mean_change']:.2f} | frames moving {s['frames_moving_pct']:.1f}%"
              f" | longest still {s['longest_still_s']:.1f}s  (information; it cannot see small-area motion on a flat page)")
        for n, v, al, ok in rows:
            print(f"  {'PASS' if ok else 'FAIL'}  {n} = {v:.2f}  (allowed {al})")
    sys.exit(0 if all(ok for *_, ok in rows) else 1)
