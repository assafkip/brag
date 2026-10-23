"""Render an HTML page straight into an mp4: frames are piped into ffmpeg and never touch the disk as PNGs.

  uv run --with playwright python render_pipe.py --page index.html --total 28 --poster-at 11 --out renders/noaudio.mp4

Same page contract as render_frames.py (window.render(t), 1920x1080, 30 fps, h264 crf 17, yuv420p). Prefer this over
render_frames.py when the disk is tight (28 s at 30 fps is about 840 PNGs), when the page is heavy (three.js, route R4),
or whenever you do not need the individual frames afterwards. Prefer render_frames.py when you want to look at or
re-use single frames. Mux the audio afterwards with ffmpeg or mux.sh from a frames folder.

Disk guard: every --check-every frames the free space on the volume that holds the output is checked. Below
--min-free-mib the run stops cleanly (ffmpeg is closed so the partial mp4 is valid), says so and exits 3. A full disk
once ended a render in a corrupt file and, worse, took other work down with it.

Frame 0 is drawn at --poster-at, so the poster frame is baked into the video's first frame (--poster-out also saves it).
Chrome runs with its disk and media caches cut to one byte so a long render does not fill the cache directory.
Optional: --wait-for "<js expression>" waits until a page-ready flag is true (for example textures loaded);
--chrome-arg passes extra flags (for example --enable-gpu for a WebGL page).
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

CACHE_FLAGS = ["--disk-cache-size=1", "--media-cache-size=1"]


def free_mib(path):
    return shutil.disk_usage(path).free / 2**20


def space_ok(path, floor_mib, free_fn=free_mib):
    """(ok, free_mib). The volume is the one holding `path`; free_fn is injectable so a low value can be faked."""
    free = free_fn(path)
    return free >= floor_mib, free


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    ap.add_argument("--total", type=float, required=True)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--poster-at", type=float, default=None, help="time drawn as frame 0 (default: t=0)")
    ap.add_argument("--poster-out")
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-free-mib", type=float, default=500)
    ap.add_argument("--check-every", type=int, default=15)
    ap.add_argument("--channel", default="chrome")
    ap.add_argument("--wait-for")
    ap.add_argument("--chrome-arg", action="append", default=[])
    a = ap.parse_args(argv)
    from playwright.sync_api import sync_playwright   # imported here so the guard functions import without it

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    times = [i / a.fps for i in range(int(round(a.total * a.fps)))]
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(a.fps), "-c:v", "png", "-i", "-",
                           "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b = p.chromium.launch(channel=a.channel, headless=True, args=CACHE_FLAGS + a.chrome_arg)
        page = b.new_page(viewport={"width": a.width, "height": a.height}, device_scale_factor=1)
        page.goto(Path(a.page).resolve().as_uri())
        page.evaluate("() => document.fonts.ready")
        if a.wait_for:
            page.wait_for_function(a.wait_for)
        t0 = time.time()
        for i, t in enumerate(times):
            if i % a.check_every == 0:
                ok, free = space_ok(out.parent, a.min_free_mib)
                print(f"frame {i} free_MiB {free:.0f}", flush=True)
                if not ok:
                    ff.stdin.close()
                    ff.wait()
                    b.close()
                    print(f"STOP low disk at frame {i}: {free:.0f} MiB free is under the {a.min_free_mib:.0f} MiB floor. Partial video kept at {out}.", flush=True)
                    return 3
            page.evaluate("(t) => window.render(t)", a.poster_at if (i == 0 and a.poster_at is not None) else t)
            data = page.screenshot(type="png")
            if i == 0 and a.poster_out:
                Path(a.poster_out).write_bytes(data)
            ff.stdin.write(data)
        ff.stdin.close()
        ff.wait()
        print(f"{len(times)} frames in {time.time() - t0:.1f}s -> {out}")
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
