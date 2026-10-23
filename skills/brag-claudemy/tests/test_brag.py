"""Known-answer tests for the brag skill's scripts.

Each test has a case that must pass and a case that must fail, so a green run means the check can fail.
Run:  python3 -m pytest tests -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SK / "scripts"))
import copylint  # noqa: E402
import pace  # noqa: E402

DL = Path.home() / "Downloads"
R1, R2 = DL / "claudemy-sonos-cut.mp4", DL / "claudemy-sonos-cut-v2.mp4"


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


# ---- pace.py: reproduces the founder's recorded results ---------------------------------------
@pytest.mark.skipif(not (R1.exists() and R2.exists()), reason="the owner's two reference renders are not in ~/Downloads; this known-answer check only runs on the owner's machine")
def test_pace_reproduces_recorded_results():
    s1, s2 = pace.measure(str(R1)), pace.measure(str(R2))
    # recorded in the owner's Claudemy notes: render 1 mean 3.64, moving 71%, longest still 2.6s, changes at 4.5 8.5 12.5 16.5 21.0
    assert abs(s1["mean_change"] - 3.64) < 0.1
    assert abs(s1["frames_moving_pct"] - 71) < 3
    assert abs(s1["longest_still_s"] - 2.6) < 0.15
    assert s1["shot_changes_s"] == [4.5, 8.5, 12.5, 16.5, 21.0]
    assert abs(s1["avg_shot_s"] - 4.25) < 0.01
    assert abs(s2["mean_change"] - 4.18) < 0.1  # render 2 recorded mean change
    assert s2["shot_changes_s"] == [4.5, 8.5, 12.5, 16.5, 21.5]


def test_pace_static_vs_moving(tmp_path):
    static, moving = tmp_path / "static.mp4", tmp_path / "moving.mp4"
    ff("-f", "lavfi", "-i", "color=c=gray:s=640x360:d=4:r=30", "-pix_fmt", "yuv420p", str(static))
    ff("-f", "lavfi", "-i", "testsrc2=s=640x360:d=4:r=30", "-pix_fmt", "yuv420p", str(moving))
    a, b = pace.measure(str(static)), pace.measure(str(moving))
    assert a["frames_moving_pct"] == 0 and a["longest_still_s"] >= 3.8   # must read as still
    assert b["frames_moving_pct"] > 95 and b["longest_still_s"] < 0.3    # must read as moving


# ---- copylint.py ---------------------------------------------------------------------------------
def test_copylint_flags_and_ignores():
    bad = "A line — with a dash. And a -- double. This is AI-powered. Costs $5."
    kinds = [r for _, r, _ in copylint.lint_text(bad, forbidden_patterns=[r"\$\s?\d"])]
    assert "emdash" in kinds and "double hyphen" in kinds
    assert any("banned" in k for k in kinds) and any("forbidden pattern" in k for k in kinds)
    assert copylint.lint_text("Plain text, one hyphen-ated word, a divider ---") == []


def test_copylint_html_css_variable_is_not_copy(tmp_path):
    ok = tmp_path / "ok.html"
    ok.write_text('<style>:root{--ink:#000}</style><div style="color:var(--ink)">Hello</div>')
    assert copylint.lint_files([ok])[str(ok)] == []
    bad = tmp_path / "bad.html"
    bad.write_text("<div>Hello &mdash; world</div>")
    assert any(r == "emdash" for _, r, _ in copylint.lint_files([bad])[str(bad)])


# ---- audio.py ---------------------------------------------------------------------------------------
def test_audio_plan_renders(tmp_path):
    import audio
    import wave
    plan = json.loads((SK / "templates" / "audio-plan.json").read_text())
    plan["total"], plan["out"] = 4.0, "t.wav"
    plan["bed"] = [{"at": 0.0, "chord": "Dm"}, {"at": 2.0, "chord": "F", "bass": True, "arp": True}]
    plan["ring"] = {"at": 3.0, "midi": 72}
    plan["foley"] = [{"at": 1.0, "n": 1, "cut": 1800, "gain": 0.08}]
    out, total = audio.build(plan, str(tmp_path))
    with wave.open(str(out)) as w:
        assert abs(w.getnframes() / w.getframerate() - 4.0) < 0.01 and w.getnchannels() == 2


# ---- scaffold.sh ------------------------------------------------------------------------------------
def test_scaffold_concept_and_built(tmp_path):
    for mode, expect in (("concept", "STATUS: CONCEPT"), ("built", "STATUS: BUILT")):
        d = tmp_path / mode
        subprocess.run(["bash", str(SK / "scripts" / "scaffold.sh"), str(d), "Test Product", mode], check=True, capture_output=True)
        assert expect in (d / "BRIEF.md").read_text()
        for f in ("rulings.md", "rulings.json", "SCRIPT.md", "STORYBOARD.md", "DESIGN.md", "reference.json", "audio-plan.json", "index.html"):
            assert (d / f).exists(), f
    assert json.loads((tmp_path / "concept" / "rulings.json").read_text())["forbidden_patterns"]
    assert not json.loads((tmp_path / "built" / "rulings.json").read_text())["forbidden_patterns"]
    assert 'id="concept-label"' in (tmp_path / "concept" / "index.html").read_text()


# ---- verify.py: must fail a bad video and flag a missing source tag --------------------------------
def test_verify_fails_bad_project(tmp_path):
    d = tmp_path / "p"
    subprocess.run(["bash", str(SK / "scripts" / "scaffold.sh"), str(d), "Bad", "concept"], check=True, capture_output=True)
    (d / "SCRIPT.md").write_text("# S\n\n## On-screen text\n\n- Scene 1 line: \"No source here\"\n")
    vid = d / "renders" / "bad.mp4"
    ff("-f", "lavfi", "-i", "testsrc2=s=1920x1080:d=3:r=30", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "3",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(vid))
    p = subprocess.run([sys.executable, str(SK / "scripts" / "verify.py"), str(vid), "--project", str(d)], capture_output=True, text=True)
    assert p.returncode == 1, p.stdout
    out = p.stdout
    assert "poster" in out and "FAIL" in out and "without [src" in out and "NOT VERIFIED" in out


# ---- declared scenes: shot count comes from the page, and the scenes must tile the video -----------------
def test_declared_scenes_and_cover(tmp_path):
    (tmp_path / "index.html").write_text("<script>const SCENES = [{id:'s1', start: 0.0, end: 5.5},{id:'s2', start: 5.0, end: 10.5}];</script>")
    sc = pace.declared_scenes(tmp_path)
    assert sc == [(0.0, 5.5), (5.0, 10.5)]
    assert pace.scenes_cover(sc, 10.5)[0]
    assert not pace.scenes_cover([(0, 5), (8, 10)], 10)[0]        # a gap
    assert not pace.scenes_cover([(0, 5), (1, 10)], 10)[0]        # too much overlap
    assert not pace.scenes_cover([(2, 10)], 10)[0]                # does not start at 0
    assert not pace.scenes_cover([(0, 5)], 10)[0]                 # does not reach the end


def _mk_project(tmp_path, scenes_js):
    d = tmp_path / "p"
    subprocess.run(["bash", str(SK / "scripts" / "scaffold.sh"), str(d), "Pace", "concept"], check=True, capture_output=True)
    page = (d / "index.html").read_text()
    import re
    (d / "index.html").write_text(re.sub(r"const SCENES = \[.*?\];", "const SCENES = " + scenes_js + ";", page, flags=re.S))
    (d / "SCRIPT.md").write_text("# S\n\n## On-screen text\n\n- Scene 1 label: \"The problem\" [src: X-1]\n\nConcept preview\n")
    vid = d / "renders" / "v.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:d=12:r=30", "-f", "lavfi",
                    "-i", "sine=f=220:d=12", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(vid)], check=True)
    return d, vid


def test_verify_pace_uses_declared_scenes_and_refuses_a_bad_table(tmp_path):
    good, vid = _mk_project(tmp_path, "[{id:'a',start:0,end:4.2},{id:'b',start:4,end:8.2},{id:'c',start:8,end:12}]")
    out = subprocess.run([sys.executable, str(SK / "scripts" / "verify.py"), str(vid), "--project", str(good)], capture_output=True, text=True).stdout
    line = next(l for l in out.splitlines() if l.startswith("pace"))
    assert "PASS" in line and "3 scenes from index.html" in line, out       # 12 s / 3 scenes = 4.0 s, inside 3.5 to 4.8
    bad, vid2 = _mk_project(tmp_path / "x", "[{id:'a',start:0,end:3},{id:'b',start:6,end:12}]")   # a 3 second gap
    out2 = subprocess.run([sys.executable, str(SK / "scripts" / "verify.py"), str(vid2), "--project", str(bad)], capture_output=True, text=True).stdout
    assert next(l for l in out2.splitlines() if l.startswith("pace")).split()[1] == "FAIL", out2


# ---- mux.sh: two-pass loudness lands on target ----------------------------------------------------------
def test_mux_lands_on_minus_16(tmp_path):
    frames = tmp_path / "frames"
    frames.mkdir()
    ff("-f", "lavfi", "-i", "testsrc2=s=320x180:d=4:r=30", str(frames / "%05d.png"))
    ff("-f", "lavfi", "-i", "sine=f=330:d=4", "-af", "volume=0.35", "-ar", "48000", "-ac", "2", str(tmp_path / "a.wav"))
    out = tmp_path / "o.mp4"
    subprocess.run(["bash", str(SK / "scripts" / "mux.sh"), str(frames), str(tmp_path / "a.wav"), str(out), "1.0"], check=True, capture_output=True)
    import verify
    ld = verify.loudness(str(out))
    assert abs(float(ld["input_i"]) + 16) < 0.7, ld
