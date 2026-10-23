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
