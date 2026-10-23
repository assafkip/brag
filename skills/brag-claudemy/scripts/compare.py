#!/usr/bin/env python3
"""Compare a produced video with its reference, with the same instrument, side by side.

  uv run --with numpy --with pillow python compare.py <reference.mp4> <produced.mp4>
        [--range 0:7] [--ref-range 0:7] [--prod-range 0:7] [--frames 6] [--sheet compare-sheet.png]

Runs scripts/pace.py on both videos (whole video, or a matching time range with --range, or a
different range for each with --ref-range and --prod-range), prints mean change, frames moving percent and
longest still next to each other, and writes a contact sheet: the reference on the top row, the produced video
on the bottom row, --frames columns, each pair sampled at the same RELATIVE time of its range and labelled.

Distance, not absence. The reference is the floor: the produced video is flagged BELOW REFERENCE when it moves
less (mean change, frames moving) or holds a still longer than the reference does, beyond --tolerance
(a fraction, default 0). There is deliberately no PASS and no "good": reaching the reference is a floor, not a
finish line (rulings.md, ruling 27). Exit 0 = nothing below the reference, 2 = at least one axis below,
3 = could not measure.

Before it trusts any number it measures a generated still clip (the control). The instrument must read that
clip as 0 percent moving, or the run stops with exit 3: a probe that is blind or broken reports "fine" about
everything.

The contact sheet needs Pillow for its labels. Without it the run still prints the table and exits with the
same code, and says the sheet was not written.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pace  # noqa: E402

AXES = (  # key, label, direction: "min" = produced must be at least the reference, "max" = at most
    ("mean_change", "mean change", "min"),
    ("frames_moving_pct", "frames moving %", "min"),
    ("longest_still_s", "longest still s", "max"),
)


def parse_range(s):
    if not s:
        return None
    a, b = s.split(":")
    a, b = float(a), float(b)
    if b <= a:
        raise ValueError(f"range {s} ends before it starts")
    return a, b


def clip(src, rng, workdir, name):
    """Cut a time range to a temporary file (re-encoded, so the cut is frame exact)."""
    out = Path(workdir) / name
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(rng[0]), "-t", str(rng[1] - rng[0]), "-i", str(src), "-an",
                    "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out


def control_reads_still(workdir):
    """The instrument's known answer: a generated gray clip must read as not moving at all."""
    c = Path(workdir) / "control.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=640x360:d=3:r=30",
                    "-pix_fmt", "yuv420p", str(c)], check=True)
    s = pace.measure(str(c))
    return s["frames_moving_pct"] == 0, s


def distance(ref, prod, tol=0.0):
    """Return (axis label, reference value, produced value, below_reference) per axis."""
    rows = []
    for key, label, direction in AXES:
        r, p = ref[key], prod[key]
        below = p < r * (1 - tol) if direction == "min" else p > r * (1 + tol)
        rows.append((label, r, p, below))
    return rows


def sample_times(rng, dur, n):
    a, b = rng if rng else (0.0, dur)
    return [a + (b - a) * (i + 0.5) / n for i in range(n)]


def grab(src, t, size):
    w, h = size
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1", "-vf", f"scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return raw if len(raw) == w * h * 3 else None


def contact_sheet(ref, prod, ref_rng, prod_rng, n, out, cell=(320, 180)):
    from PIL import Image, ImageDraw   # lazy: the table does not need it
    rd, pd = pace.duration(str(ref)), pace.duration(str(prod))
    rt, pt = sample_times(ref_rng, rd, n), sample_times(prod_rng, pd, n)
    w, h = cell
    lab = 18
    sheet = Image.new("RGB", (n * w, 2 * (h + lab)), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for row, (name, src, times) in enumerate((("REF", ref, rt), ("PROD", prod, pt))):
        for i, t in enumerate(times):
            raw = grab(src, t, cell)
            x, y = i * w, row * (h + lab)
            if raw:
                sheet.paste(Image.frombytes("RGB", cell, raw), (x, y + lab))
            d.text((x + 4, y + 3), f"{name} {t:.1f}s  ({(i + 0.5) / n:.0%} of range)", fill=(235, 235, 235))
    sheet.save(out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("reference")
    ap.add_argument("produced")
    ap.add_argument("--range", help="start:end seconds, applied to both videos")
    ap.add_argument("--ref-range")
    ap.add_argument("--prod-range")
    ap.add_argument("--frames", type=int, default=6)
    ap.add_argument("--sheet", default="compare-sheet.png")
    ap.add_argument("--tolerance", type=float, default=0.0)
    a = ap.parse_args(argv)
    try:
        rr = parse_range(a.ref_range or a.range)
        pr = parse_range(a.prod_range or a.range)
    except ValueError as e:
        print(f"could not measure: {e}")
        return 3
    for p in (a.reference, a.produced):
        if not Path(p).exists():
            print(f"could not measure: {p} not found")
            return 3
    with tempfile.TemporaryDirectory() as tmp:
        ok, ctl = control_reads_still(tmp)
        if not ok:
            print(f"could not measure: the control (a still gray clip) read {ctl['frames_moving_pct']:.1f}% moving, so this instrument cannot be trusted here")
            return 3
        ref_src = clip(a.reference, rr, tmp, "ref.mp4") if rr else Path(a.reference)
        prod_src = clip(a.produced, pr, tmp, "prod.mp4") if pr else Path(a.produced)
        ref, prod = pace.measure(str(ref_src)), pace.measure(str(prod_src))
    rows = distance(ref, prod, a.tolerance)
    span = lambda rng: f"{rng[0]:g} to {rng[1]:g} s" if rng else "whole video"
    print(f"reference: {a.reference} ({span(rr)})   produced: {a.produced} ({span(pr)})   control: still clip read 0% moving")
    print(f"{'':<18}{'reference':>10}{'produced':>10}  produced vs reference")
    for label, r, p, below in rows:
        ratio = f"{p / r:.2f}x" if r else "n/a"
        print(f"{label:<18}{r:>10.2f}{p:>10.2f}  {ratio}{'  BELOW REFERENCE' if below else ''}")
    print(f"{'shots':<18}{ref['shots']:>10}{prod['shots']:>10}  (information, not a floor)")
    try:
        contact_sheet(a.reference, a.produced, rr, pr, a.frames, a.sheet)
        print(f"contact sheet: {a.sheet} ({a.frames} columns, reference on top, produced below)")
    except ImportError:
        print("contact sheet not written: Pillow is missing (run with: uv run --with numpy --with pillow python compare.py ...)")
    except Exception as e:  # noqa: BLE001
        print(f"contact sheet not written: {type(e).__name__}: {e}")
    below = [r[0] for r in rows if r[3]]
    if below:
        print("BELOW REFERENCE: " + ", ".join(below) + ". Not a verdict either way: look at the sheet.")
        return 2
    print("Nothing below the reference. That is a floor, not a finish line: look at the sheet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
