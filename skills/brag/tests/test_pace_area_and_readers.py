"""Reproducers for ASK-3036: two checks that misfire on a narrated, UI-on-white video.

Each test generates its own fixtures, makes no network call and spends nothing.

1 pace: a whole-frame mean grey change cannot see a small element moving on a flat page.
  On the approved openwitness v7 (white plane, chips popping, rows sliding, text typing)
  pace.py read 8 percent moving and a 9.3 s longest still, so verify reported pace FAIL on
  a cut the founder approved. The clips below are that shape in miniature.

2 readers: a reader shown silent frames retold the story correctly and still said LEAVE,
  because the narration carried the beat it said was missing. The row now carries retell
  coverage next to the verdict, and readers_check reads it.

Run:  python3 -m pytest tests -q
"""
import json
import subprocess
import sys
from pathlib import Path

SK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SK / "scripts"))
import chain_checks  # noqa: E402
import pace  # noqa: E402

WHITE = "color=c=white:s=1920x1080:d=4:r=30"


def _clip(path, box_x):
    """White 1920x1080 for 4 s with one 40 by 40 black block at box_x (an ffmpeg expression)."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", WHITE,
                    # eval=frame or drawbox resolves x once and the block never moves
                    "-vf", f"drawbox=x='{box_x}':y=500:w=40:h=40:color=black:t=fill:eval=frame",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", str(path)], check=True)
    return path


def _clips(tmp_path):
    return (_clip(tmp_path / "frozen.mp4", "900"),
            _clip(tmp_path / "moving.mp4", "100+t*200"))


# ---- 1 pace ------------------------------------------------------------------------------------
def test_tile_instrument_sees_a_small_block_the_whole_frame_mean_misses(tmp_path):
    frozen, moving = _clips(tmp_path)
    f, m = pace.measure(str(frozen)), pace.measure(str(moving))

    # the bug, stated as a measurement: the whole-frame mean reads the moving clip as still
    assert m["frames_moving_pct"] < 20, m
    assert m["longest_still_s"] > 2.0, m

    # the fix: the tile instrument separates the two clips
    assert m["area_moving_pct"] > 90, m
    assert m["longest_area_still_s"] < 0.5, m
    assert f["area_moving_pct"] == 0, f
    assert f["longest_area_still_s"] >= 3.5, f


def test_pace_compare_gates_the_tile_instrument(tmp_path):
    frozen, moving = _clips(tmp_path)
    ref = {"frames_moving_pct_range": [55, 100], "longest_still_s_max": 1.0}
    bad = pace.compare(pace.measure(str(frozen)), ref)
    good = pace.compare(pace.measure(str(moving)), ref)
    assert [n for n, *_ in bad] == ["area_moving_pct", "longest_area_still_s"], bad
    assert not any(ok for *_, ok in bad), bad          # red on the frozen clip
    assert all(ok for *_, ok in good), good            # green on the moving one


def test_verify_reports_the_whole_frame_mean_as_info(tmp_path):
    d = tmp_path / "p"
    subprocess.run(["bash", str(SK / "scripts" / "scaffold.sh"), str(d), "Area", "concept"],
                   check=True, capture_output=True)
    (d / "SCRIPT.md").write_text("# S\n\n## On-screen text\n\n- Scene 1 label: \"The problem\" [src: X-1]\n\nConcept preview\n")
    vid = d / "renders" / "v.mp4"
    _clip(tmp_path / "m.mp4", "100+t*200")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp_path / "m.mp4"), "-f", "lavfi",
                    "-i", "sine=f=220:d=4", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", str(vid)], check=True)
    out = subprocess.run([sys.executable, str(SK / "scripts" / "verify.py"), str(vid), "--project", str(d)],
                         capture_output=True, text=True).stdout
    whole = next((l for l in out.splitlines() if l.startswith("whole-frame")), None)
    assert whole is not None and "INFO" in whole, out
    assert "not a gate" in whole, out


# ---- 2 readers ---------------------------------------------------------------------------------
def _reader_project(tmp_path, rows):
    d = tmp_path / "r"
    d.mkdir(parents=True, exist_ok=True)
    (d / "rulings.json").write_text(json.dumps({"readers_required": 2}))
    (d / "readers.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return d


def _row(reader, verdict="STAY", **extra):
    return {"reader": reader, "verdict": verdict, "why": "clear", **extra}


def test_readers_check_reports_retell_coverage(tmp_path):
    d = _reader_project(tmp_path, [_row("a", retell_matched=7, retell_total=8),
                                   _row("b", retell_matched=8, retell_total=8)])
    status, detail = chain_checks.readers_check(d)
    assert status == "PASS", (status, detail)
    assert "retell coverage" in detail and "15/16" in detail, detail


def test_readers_check_warns_on_a_row_with_no_retell_coverage(tmp_path):
    d = _reader_project(tmp_path, [_row("a", retell_matched=7, retell_total=8), _row("b")])
    status, detail = chain_checks.readers_check(d)
    assert status == "WARN", (status, detail)
    assert "b" in detail and "retell coverage" in detail, detail


def test_readers_check_fails_a_malformed_coverage_pair(tmp_path):
    d = _reader_project(tmp_path, [_row("a", retell_matched=9, retell_total=8), _row("b", retell_matched=1, retell_total=8)])
    status, detail = chain_checks.readers_check(d)
    assert status == "FAIL", (status, detail)
    assert "retell" in detail, detail


def test_reader_brief_asks_for_the_timestamped_transcript():
    brief = (SK / "references" / "reader-brief.md").read_text()
    assert "retell_matched" in brief and "retell_total" in brief, "the row fields are not specified"
    low = brief.lower()
    assert "transcript" in low and "timestamp" in low, "the brief does not hand the reader the narration"
