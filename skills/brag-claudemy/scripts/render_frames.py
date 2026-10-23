"""Render an HTML page to PNG frames, one per timestamp, in headless Chrome.

  uv run --with playwright python render_frames.py --page index.html --total 28 --out frames
  uv run --with playwright python render_frames.py --page index.html --stills 3.4,7.6,11.6 --out boards
  uv run --with playwright python render_frames.py --page index.html --total 28 --out frames --tracks laptop=motion/track-laptop.json

The page must define window.render(t): a pure function that draws the frame for time t (seconds).
Nothing may depend on real time: no CSS transitions or animations, no setTimeout, no Math.random.
Same page, same t, same pixels. Uses the installed Google Chrome (channel "chrome"), so no browser
download is needed. --tracks name=path loads corner tracks (track.py or detect_screen.py output)
into window.TRACKS[name] as a list of 4-corner quads, one per source-clip frame, for pinning a UI to a
moving screen.

Adapted from the owner's Claudemy Sonos-cut renderer (2026-10-23).
"""
import argparse
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("--page", required=True)
ap.add_argument("--total", type=float, default=0)
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--stills")
ap.add_argument("--out", required=True)
ap.add_argument("--tracks", nargs="*", default=[])
ap.add_argument("--channel", default="chrome")
a = ap.parse_args()

page_path = Path(a.page).resolve()
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
if a.stills:
    times = [float(x) for x in a.stills.split(",")]
elif a.total > 0:
    times = [i / a.fps for i in range(int(round(a.total * a.fps)))]
else:
    raise SystemExit("give --total or --stills")
tracks = {}
for spec in a.tracks:
    name, path = spec.split("=", 1)
    tracks[name] = [f["corners"] for f in json.loads(Path(path).read_text())["frames"]]

with sync_playwright() as p:
    browser = p.chromium.launch(channel=a.channel, headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    page.goto(page_path.as_uri())
    page.evaluate("(tr) => { window.TRACKS = tr; }", tracks)
    page.evaluate("() => document.fonts.ready")
    page.wait_for_function("() => [...document.images].filter(i => i.getAttribute('src')).every(i => i.complete && i.naturalWidth > 0)")
    t0 = time.time()
    for i, t in enumerate(times):
        page.evaluate("(t) => window.render(t)", t)
        name = f"t{t:05.2f}.png" if a.stills else f"{i:05d}.png"
        page.screenshot(path=str(out / name))
    print(f"{len(times)} frames in {time.time() - t0:.1f}s -> {out}")
    browser.close()
