#!/usr/bin/env python3
"""Verify a finished video against the project's done-means. Exit 1 on any FAIL.

  python3 verify.py <video.mp4> [--project DIR]

Checks (each prints PASS, FAIL or INFO):
  1 file       h264 video, AAC audio, 1920x1080, duration within the BRIEF target if it states one
  2 loudness   integrated loudness within 1.5 LU of -16 LUFS, true peak at most -1.0 dBTP
  3 pace       against <project>/reference.json (avg shot, AREA moving, longest area still). The motion gate
               reads the per-tile instrument; the whole-frame mean follows as a separate INFO row
  3b whole-frame  the whole-frame mean change, moving share and longest still, as information only
  4 poster     <video stem>-poster.jpg exists and equals frame 0 (mean difference under 10)
  5 copy       copylint over SCRIPT.md, STORYBOARD.md and the page(s) in the project root
  6 sources    every on-screen line in SCRIPT.md carries a [src: ...] tag
  7 concept    if BRIEF.md says STATUS: CONCEPT, SCRIPT.md has "Concept preview" and the page has id="concept-label".
               rulings.json "waive_concept_label": "<reason>" turns a failing result into WAIVED (reason); an empty
               reason is not a waiver and stays FAIL
  8 chain      study, craft, directions, vision, critique, readers (scripts/chain_checks.py). WARN when a required
               file is missing, INFO when an opt-in file is missing, FAIL when a file exists and its claims do not hold

Statuses: PASS, FAIL, WARN, WAIVED, INFO. Only FAIL fails the run. After the run it writes <video>.receipt.json
(the video's sha256 and every status). `verify.py <video> --check-receipt` exits 0 only if that receipt matches
the video as it is now and holds no FAIL: the check to run before showing the video to anyone.

It prints what it did NOT verify, so a clean run is never read as more than it is.
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_checks  # noqa: E402
import copylint  # noqa: E402
import pace  # noqa: E402

rows = []


def add(name, status, detail):
    rows.append((name, status, detail))


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height",
                          "-show_entries", "format=duration", "-of", "json", path], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def loudness(path):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                        "-vn", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", p.stderr, re.S)
    return json.loads(m.group(0)) if m else None


def frame0(path, size=(160, 90)):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-frames:v", "1", "-vf", f"scale={size[0]}:{size[1]},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(size[1], size[0]).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--project", default=".")
    ap.add_argument("--check-receipt", action="store_true")
    a = ap.parse_args()
    v, proj = Path(a.video), Path(a.project)
    if a.check_receipt:
        return check_receipt(v)

    # 1 file
    try:
        info = probe(str(v))
        streams = info["streams"]
        vs = next((s for s in streams if s["codec_type"] == "video"), {})
        au = next((s for s in streams if s["codec_type"] == "audio"), {})
        dur = float(info["format"]["duration"])
        ok = vs.get("codec_name") == "h264" and au.get("codec_name") == "aac" and (vs.get("width"), vs.get("height")) == (1920, 1080)
        brief = (proj / "BRIEF.md").read_text() if (proj / "BRIEF.md").exists() else ""
        tgt = re.search(r"Duration target:\s*(\d+(?:\.\d+)?)", brief)
        extra = ""
        if tgt:
            t = float(tgt.group(1))
            if abs(dur - t) > 3:
                ok = False
            extra = f", target {t:g}s"
        add("file", "PASS" if ok else "FAIL", f"{vs.get('codec_name')}/{au.get('codec_name')} {vs.get('width')}x{vs.get('height')}, {dur:.1f}s{extra}")
    except Exception as e:  # noqa: BLE001
        add("file", "FAIL", f"cannot read video: {e}")
        return finish()

    # 2 loudness
    ld = loudness(str(v))
    if ld:
        i, tp = float(ld["input_i"]), float(ld["input_tp"])
        add("loudness", "PASS" if abs(i + 16) <= 1.5 and tp <= -1.0 else "FAIL", f"{i:.1f} LUFS, true peak {tp:.1f} dBTP")
    else:
        add("loudness", "FAIL", "could not measure (no audio?)")

    # 3 pace
    ref = proj / "reference.json"
    if ref.exists():
        s = pace.measure(str(v))
        decl, note, cover_fail = pace.declared_scenes(proj), "", None
        if decl:
            ok_cover, why = pace.scenes_cover(decl, s["duration_s"])
            if ok_cover:
                n = len(decl)
                s = {**s, "shots": n, "avg_shot_s": s["duration_s"] / n}
                note = (f" | {n} scenes from index.html SCENES; the pixel detector sees {len(s['shot_changes_s'])} of {n - 1} changes"
                        " (it cannot see soft dissolves between similar scenes)")
            else:
                cover_fail = why
        if cover_fail:
            add("pace", "FAIL", f"index.html SCENES table does not tile the video: {cover_fail}")
        else:
            res = pace.compare(s, json.load(open(ref)))
            bad = [r for r in res if not r[3]]
            add("pace", "FAIL" if bad else "PASS",
                f"avg shot {s['avg_shot_s']:.2f}s, area moving {s['area_moving_pct']:.0f}%, longest area still {s['longest_area_still_s']:.1f}s"
                + (" | out of range: " + ", ".join(r[0] for r in bad) if bad else "") + note)
        add("whole-frame", "INFO",
            f"mean change {s['mean_change']:.2f}, moving {s['frames_moving_pct']:.0f}%, longest still {s['longest_still_s']:.1f}s"
            " (not a gate: a mean over the whole frame cannot see small-area motion on a flat page, ASK-3036)")
    else:
        add("pace", "INFO", "no reference.json in the project; pace measured nowhere")

    # 4 poster
    poster = v.with_name(v.stem + "-poster.jpg")
    if poster.exists():
        diff = float(np.abs(frame0(str(v)) - frame0(str(poster))).mean())
        add("poster", "PASS" if diff < 10 else "FAIL", f"frame 0 vs poster mean difference {diff:.2f}")
    else:
        add("poster", "FAIL", f"{poster.name} not found")

    # 5 copy
    files = [p for p in (proj / "SCRIPT.md", proj / "STORYBOARD.md", proj / "narration.txt") if p.exists()] + sorted(proj.glob("*.html"))
    rl = json.load(open(proj / "rulings.json")) if (proj / "rulings.json").exists() else {}
    found = [(f, i) for f, items in copylint.lint_files(files, rl).items() for i in items]
    add("copy", "FAIL" if found else "PASS", f"{len(files)} file(s) linted" + ("; " + "; ".join(f"{Path(f).name}:{n} {r}" for f, (n, r, _) in found[:4]) if found else ""))

    # 6 sources
    sc = proj / "SCRIPT.md"
    if sc.exists():
        lines, in_block = [], False
        for line in sc.read_text().splitlines():
            if line.startswith("## "):
                in_block = line.lower().startswith("## on-screen text")
            elif in_block and line.startswith("- "):
                lines.append(line)
        miss = [l for l in lines if "[src:" not in l]
        add("sources", "FAIL" if (miss or not lines) else "PASS", f"{len(lines)} on-screen line(s), {len(miss)} without [src: ...]" if lines else "no on-screen lines found under '## On-screen text'")
    else:
        add("sources", "FAIL", "SCRIPT.md not found")

    # 7 concept
    brief = (proj / "BRIEF.md").read_text() if (proj / "BRIEF.md").exists() else ""
    if re.search(r"^STATUS:\s*CONCEPT", brief, re.M):
        script_ok = sc.exists() and "Concept preview" in sc.read_text()
        page_ok = any('id="concept-label"' in p.read_text() for p in proj.glob("*.html"))
        detail = f"script label {'yes' if script_ok else 'MISSING'}, page label element {'yes' if page_ok else 'MISSING'}"
        waive = rl.get("waive_concept_label")
        if script_ok and page_ok:
            add("concept", "PASS", detail)
        elif isinstance(waive, str) and waive.strip():
            add("concept", "WAIVED", f"({waive.strip()}) {detail}")
        elif "waive_concept_label" in rl:
            add("concept", "FAIL", f"{detail}; waive_concept_label needs a non-empty reason string, so it waives nothing")
        else:
            add("concept", "FAIL", detail)
    else:
        add("concept", "INFO", "BRIEF.md does not say STATUS: CONCEPT")

    # 8 chain
    for name, status, detail in chain_checks.run_all(proj, v):
        add(name, status, detail)
    return finish(v)


def check_receipt(v):
    r = v.with_name(v.stem + ".receipt.json")
    if not r.exists():
        print(f"NO RECEIPT: {r.name} not found. Run verify.py on this video first.")
        return 1
    rec = json.loads(r.read_text())
    if rec.get("video_sha256") != chain_checks.sha256(v):
        print("STALE RECEIPT: the video changed after it was verified. Run verify.py again.")
        return 1
    if rec.get("fail"):
        print(f"RECEIPT HOLDS {rec['fail']} FAIL: not ready to show.")
        return 1
    print(f"RECEIPT OK: {rec['written']} for this exact video, no FAIL.")
    return 0


def finish(video=None):
    w = max(len(r[0]) for r in rows)
    for n, s, d in rows:
        print(f"{n:<{w}}  {s:<6} {d}")
    count = {k: sum(1 for r in rows if r[1] == k) for k in ("PASS", "FAIL", "WARN", "WAIVED", "INFO")}
    print(f"\nSUMMARY: {count['PASS']} PASS, {count['FAIL']} FAIL, {count['WARN']} WARN, {count['WAIVED']} WAIVED, {count['INFO']} INFO")
    print("NOT VERIFIED by this script: visual quality and taste, whether each claim is true beyond its [src:] tag, brand fidelity,")
    print("that the concept label is visible in every frame, music and sound design, whether speech ends on a natural pause.")
    print("A run with no FAIL is necessary, not proof the look is right: look at the video (rulings.md, ruling 25).")
    if video is not None:
        try:
            rec = {"video": Path(video).name, "video_sha256": chain_checks.sha256(video), "fail": count["FAIL"],
                   "written": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "checks": [{"name": n, "status": s} for n, s, _ in rows]}
            Path(video).with_name(Path(video).stem + ".receipt.json").write_text(json.dumps(rec, indent=2))
        except OSError as e:
            print(f"(could not write receipt: {e})")
    return 1 if count["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
