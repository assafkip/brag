"""Known-answer tests for the 2026-10-23 additions: copylint phrases and periods, verify waiver and chain checks,
compare, voice, render_pipe guard, the R4 page. Each test has a case that passes and a case that fails.
Run:  python3 -m pytest tests -q
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SK / "scripts"))
import chain_checks  # noqa: E402
import compare  # noqa: E402
import copylint  # noqa: E402
import render_pipe  # noqa: E402
import voice  # noqa: E402


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def scaffold(tmp_path, name="p", mode="concept"):
    d = tmp_path / name
    subprocess.run(["bash", str(SK / "scripts" / "scaffold.sh"), str(d), "T", mode], check=True, capture_output=True)
    return d


def make_video(d, name="v.mp4", secs=3):
    v = d / "renders" / name
    ff("-f", "lavfi", "-i", f"testsrc2=s=1920x1080:d={secs}:r=30", "-f", "lavfi", "-i", "sine=f=220:d=%d" % secs,
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v))
    return v


def run_verify(d, v, *extra):
    return subprocess.run([sys.executable, str(SK / "scripts" / "verify.py"), str(v), "--project", str(d), *extra],
                          capture_output=True, text=True)


def line(out, name):
    return next(l for l in out.splitlines() if l.split()[:1] == [name])


# ---- 1 copylint allowed phrases ---------------------------------------------------------------------
def test_allowed_phrase_exempts_only_inside_the_phrase():
    pats, ok = [r"\b\d+x\b"], ["10x, founder's estimate"]
    assert copylint.lint_text("10x, founder's estimate", forbidden_patterns=pats, allowed_phrases=ok) == []
    assert copylint.lint_text("12x, founder's estimate", forbidden_patterns=pats, allowed_phrases=ok)      # variant fails
    assert copylint.lint_text("10x faster", forbidden_patterns=pats, allowed_phrases=ok)                     # bare use fails
    assert copylint.lint_text("10x, founder's estimate and 5x", forbidden_patterns=pats, allowed_phrases=ok)  # second match is not covered
    assert copylint.lint_text("Acme", forbidden_words=["acme"], allowed_phrases=["Acme"]) == []
    assert copylint.lint_text("Acme", forbidden_words=["acme"])


def test_allowed_phrases_through_rulings_file(tmp_path):
    f = tmp_path / "SCRIPT.md"
    f.write_text("## On-screen text\n\n- \"10x, founder's estimate\" [src: A]\n")
    rl = {"forbidden_patterns": [r"\b\d+x\b"], "allowed_phrases": ["10x, founder's estimate"]}
    assert copylint.lint_files([f], rl)[str(f)] == []
    f.write_text("## On-screen text\n\n- \"12x, founder's estimate\" [src: A]\n")
    assert copylint.lint_files([f], rl)[str(f)]


# ---- 3 no final period ------------------------------------------------------------------------------
@pytest.mark.parametrize("text", ["This is a sentence.", "It costs 5.", "Done. Next", 'He said "stop."', "wait..."])
def test_no_final_period_flags(text):
    assert copylint.period_findings(text)


@pytest.mark.parametrize("text", ["Takes 2.3 s", "assets/take1.mp3 is the track", "narration.txt and index.html", "v1.2.3 ships",
                                  "a, b: c?", "example.test is invented", "Line one [src: SPEC-1.2]"])
def test_no_final_period_ignores(text):
    assert copylint.period_findings(text) == []


def test_no_final_period_scopes_files(tmp_path):
    rl = {"no_final_period": True}
    s = tmp_path / "SCRIPT.md"
    s.write_text("# S\n\n## On-screen text\n\n- Label: \"Plain line\" [src: A]\n\n## Share copy\n\nA sentence with a period.\n")
    assert copylint.lint_files([s], rl)[str(s)] == []                      # share copy is not on screen
    s.write_text("# S\n\n## On-screen text\n\n- Label: \"Plain line.\" [src: A]\n")
    assert copylint.lint_files([s], rl)[str(s)]
    n = tmp_path / "narration.txt"
    n.write_text("One sentence without a stop\n\nAnother one, 3.5 times\n")
    assert copylint.lint_files([n], rl)[str(n)] == []
    n.write_text("One sentence.\n")
    assert copylint.lint_files([n], rl)[str(n)]
    h = tmp_path / "index.html"
    h.write_text("<style>a{b:1.5px}</style><div>Hello</div><div>take1.mp3</div><script>var x = 'a.';</script>")
    assert copylint.lint_files([h], rl)[str(h)] == []
    h.write_text("<div>Hello there.</div>")
    assert copylint.lint_files([h], rl)[str(h)]
    assert copylint.lint_files([n], {})[str(n)] == []                      # off unless asked


# ---- 2 verify waiver, receipt, statuses --------------------------------------------------------------
def test_verify_concept_waiver_needs_a_reason(tmp_path):
    d = scaffold(tmp_path)
    page = (d / "index.html").read_text().replace('id="concept-label"', 'id="x"')
    (d / "index.html").write_text(page)
    v = make_video(d)
    out = run_verify(d, v).stdout
    assert line(out, "concept").split()[1] == "FAIL", out
    (d / "rulings.json").write_text(json.dumps({"waive_concept_label": "client approved a label-free cut on 2026-10-23"}))
    out = run_verify(d, v).stdout
    assert line(out, "concept").split()[1] == "WAIVED" and "client approved" in line(out, "concept"), out
    assert re.search(r"[1-9]\d* WAIVED", out) and "0 WAIVED" not in out
    (d / "rulings.json").write_text(json.dumps({"waive_concept_label": "   "}))
    out = run_verify(d, v).stdout
    assert line(out, "concept").split()[1] == "FAIL" and "non-empty reason" in out, out


def test_verify_receipt_binds_to_the_video(tmp_path):
    d = scaffold(tmp_path)
    v = make_video(d)
    assert run_verify(d, v, "--check-receipt").returncode == 1               # no receipt yet
    run_verify(d, v)
    receipt = json.loads(v.with_name("v.receipt.json").read_text())
    assert receipt["video_sha256"] and "checks" in receipt
    # the scaffolded project fails some checks (no poster), so the receipt must hold a FAIL and refuse
    assert receipt["fail"] >= 1 and run_verify(d, v, "--check-receipt").returncode == 1
    receipt["fail"] = 0
    v.with_name("v.receipt.json").write_text(json.dumps(receipt))
    assert run_verify(d, v, "--check-receipt").returncode == 0               # clean receipt for this exact video
    make_video(d, secs=4)                                                    # the video changes
    assert "STALE" in run_verify(d, v, "--check-receipt").stdout


# ---- 8 STUDY check ---------------------------------------------------------------------------------
def study(n, placeholders=0):
    lines = ["# STUDY", "", "## A. Techniques seen (each cites a time)", ""]
    lines += [f"{i + 1}. {i}.0 to {i + 1}.0 s: panels arrive" for i in range(n)]
    lines += [f"{n + i + 1}. {{{{time: placeholder}}}} 1.0 s" for i in range(placeholders)]
    lines += ["", "## B. Forensics", "", "- 5.0 s: not a technique line"]
    return "\n".join(lines)


def test_study_check(tmp_path):
    assert chain_checks.study_check(tmp_path)[0] == "WARN"                     # missing file warns, not fails
    (tmp_path / "STUDY.md").write_text(study(11))
    st, why = chain_checks.study_check(tmp_path)
    assert st == "WARN" and "11 cited" in why
    (tmp_path / "STUDY.md").write_text(study(12))
    assert chain_checks.study_check(tmp_path)[0] == "PASS"
    (tmp_path / "STUDY.md").write_text(study(6, placeholders=8))               # unfilled template lines do not count
    assert chain_checks.study_check(tmp_path)[0] == "WARN"
    (tmp_path / "STUDY.md").write_text(study(12))
    (tmp_path / "reference.json").write_text(json.dumps({"references": ["Alpha reel"]}))
    assert chain_checks.study_check(tmp_path)[0] == "WARN"                     # a named reference is absent
    assert chain_checks.study_check(tmp_path)[0] == "WARN"
    (tmp_path / "STUDY.md").write_text(study(12) + "\nAlpha reel measured above\n")
    assert chain_checks.study_check(tmp_path)[0] == "PASS"


def test_scaffold_study_template_warns_and_verify_prints_it(tmp_path):
    d = scaffold(tmp_path)
    assert (d / "STUDY.md").exists() and (d / "DIRECTIONS.md").exists()
    assert chain_checks.study_check(d)[0] == "WARN"                            # the empty template is not a study
    assert chain_checks.directions_check(d)[0] == "WARN"
    out = run_verify(d, make_video(d)).stdout
    assert line(out, "study").split()[1] == "WARN" and "WARN" in out.split("SUMMARY:")[1]


# ---- craft, directions, vision, critique, readers --------------------------------------------------
def test_craft_check(tmp_path):
    assert chain_checks.craft_check(tmp_path)[0] == "WARN"
    (tmp_path / "STUDY.md").write_text("A. 2.0 to 4.5 s: camera drifts\n")
    (tmp_path / "index.html").write_text("<script>camera.position.set(0,0,1); /* outCubic in a comment */</script>")
    man = {"techniques": [{"id": "drift", "reference": "2.0 to 4.5 s", "fingerprint": ["camera\\.position"]}]}
    (tmp_path / "craft.json").write_text(json.dumps(man))
    assert chain_checks.craft_check(tmp_path)[0] == "PASS"
    man["techniques"][0]["fingerprint"] = ["outCubic"]                         # only in a comment: absent
    (tmp_path / "craft.json").write_text(json.dumps(man))
    assert chain_checks.craft_check(tmp_path)[0] == "FAIL"
    man["techniques"][0].update(fingerprint=["camera"], reference="9.9 s")     # cites a time the study lacks
    (tmp_path / "craft.json").write_text(json.dumps(man))
    assert chain_checks.craft_check(tmp_path)[0] == "FAIL"
    (tmp_path / "craft.json").write_text(json.dumps({"techniques": []}))
    assert chain_checks.craft_check(tmp_path)[0] == "FAIL"


def test_directions_vision_critique(tmp_path):
    (tmp_path / "DIRECTIONS.md").write_text("## One\n## Two\n")
    assert chain_checks.directions_check(tmp_path)[0] == "WARN"
    (tmp_path / "DIRECTIONS.md").write_text("## One\n## Two\n### Three\n")
    assert chain_checks.directions_check(tmp_path)[0] == "PASS"
    (tmp_path / "DIRECTIONS.md").write_text("Implements: direction 2, approved 2026-10-23\n")
    assert chain_checks.directions_check(tmp_path)[0] == "PASS"
    (tmp_path / "BRIEF.md").write_text("## Vision\n\n> {{a line in their words}}\n")
    assert chain_checks.vision_check(tmp_path)[0] == "WARN"
    (tmp_path / "BRIEF.md").write_text("## Vision\n\n> It should feel like a camera moving through the product\n\n## Brief\n")
    assert chain_checks.vision_check(tmp_path)[0] == "PASS"
    assert chain_checks.critique_check(tmp_path)[0] == "INFO"
    (tmp_path / "CRITIQUE.md").write_text("WEAK[pace]: too still\nWEAK[type]: small\nDISPOSITION[pace]: fixed, moving 80%\n")
    st, why = chain_checks.critique_check(tmp_path)
    assert st == "FAIL" and "type" in why
    (tmp_path / "CRITIQUE.md").write_text("WEAK[pace]: too still\nDISPOSITION[pace]: fixed\n")
    assert chain_checks.critique_check(tmp_path)[0] == "PASS"


def test_readers_check(tmp_path):
    vid = tmp_path / "v.mp4"
    vid.write_bytes(b"one")
    sha = chain_checks.sha256(vid)
    assert chain_checks.readers_check(tmp_path, vid)[0] == "INFO"
    (tmp_path / "rulings.json").write_text(json.dumps({"readers_required": 2}))
    row = lambda r, v, s=sha: json.dumps({"reader": r, "verdict": v, "why": "x", "video_sha256": s})
    (tmp_path / "readers.jsonl").write_text(row("a", "STAY") + "\n")
    assert chain_checks.readers_check(tmp_path, vid)[0] == "FAIL"              # one of two
    (tmp_path / "readers.jsonl").write_text(row("a", "STAY") + "\n" + row("b", "STAY") + "\n")
    assert chain_checks.readers_check(tmp_path, vid)[0] == "PASS"
    (tmp_path / "readers.jsonl").write_text(row("a", "STAY") + "\n" + row("b", "LEAVE") + "\n")
    assert chain_checks.readers_check(tmp_path, vid)[0] == "FAIL"
    (tmp_path / "readers.jsonl").write_text(row("a", "STAY", "old") + "\n" + row("b", "STAY", "old") + "\n")
    assert chain_checks.readers_check(tmp_path, vid)[0] == "FAIL"              # rows for an older render do not count


# ---- 4 compare ----------------------------------------------------------------------------------------
def test_compare_flags_a_still_video_and_writes_a_sheet(tmp_path):
    moving, still = tmp_path / "moving.mp4", tmp_path / "still.mp4"
    ff("-f", "lavfi", "-i", "testsrc2=s=640x360:d=5:r=30", "-pix_fmt", "yuv420p", str(moving))
    ff("-f", "lavfi", "-i", "color=c=gray:s=640x360:d=5:r=30", "-pix_fmt", "yuv420p", str(still))
    sheet = tmp_path / "s.png"
    p = subprocess.run([sys.executable, str(SK / "scripts" / "compare.py"), str(moving), str(still), "--sheet", str(sheet), "--frames", "4"],
                       capture_output=True, text=True)
    assert p.returncode == 2, p.stdout + p.stderr
    assert "BELOW REFERENCE" in p.stdout and "frames moving %" in p.stdout and "longest still s" in p.stdout and "mean change" in p.stdout
    same = subprocess.run([sys.executable, str(SK / "scripts" / "compare.py"), str(moving), str(moving), "--sheet", str(tmp_path / "s2.png")],
                          capture_output=True, text=True)
    assert same.returncode == 0 and "PASS" not in same.stdout, same.stdout
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed: table checked, sheet not")
    im = Image.open(sheet)
    assert im.size[0] == 4 * 320 and im.size[1] == 2 * (180 + 18)


def test_compare_range_and_missing_file(tmp_path):
    moving = tmp_path / "m.mp4"
    ff("-f", "lavfi", "-i", "testsrc2=s=640x360:d=6:r=30", "-pix_fmt", "yuv420p", str(moving))
    p = subprocess.run([sys.executable, str(SK / "scripts" / "compare.py"), str(moving), str(moving), "--range", "1:4", "--sheet", str(tmp_path / "r.png")],
                       capture_output=True, text=True)
    assert p.returncode == 0 and "1 to 4 s" in p.stdout, p.stdout
    assert compare.main([str(tmp_path / "nope.mp4"), str(moving)]) == 3


# ---- 5 voice -----------------------------------------------------------------------------------------------
def test_voice_gate_and_dry_run(tmp_path, monkeypatch, capsys):
    (tmp_path / "narration.txt").write_text("First sentence here\n\nSecond one follows\n")
    (tmp_path / "BRIEF.md").write_text("- Spend approved: none\n")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk-secret-sentinel")
    assert voice.main(["--voice-id", "abc", "--project", str(tmp_path)]) == 2             # refused: no approved line
    assert "REFUSED" in capsys.readouterr().out
    assert voice.main(["--voice-id", "abc", "--project", str(tmp_path), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "sk-secret-sentinel" not in out and "DRY RUN" in out and '"stability": 0.4' in out and '"similarity_boost": 0.75' in out
    assert '"style": 0.2' in out and '"use_speaker_boost": true' in out and "with-timestamps" in out and "39 characters" in out
    assert not (tmp_path / "narration.mp3").exists() and not (tmp_path / "spend.log").exists()
    (tmp_path / "BRIEF.md").write_text("- Spend approved: up to $5 for ElevenLabs narration\n")
    monkeypatch.delenv("ELEVENLABS_API_KEY")
    assert voice.main(["--voice-id", "abc", "--project", str(tmp_path)]) == 2             # approved, but no key
    assert "ELEVENLABS_API_KEY" in capsys.readouterr().out


def test_voice_approval_forms():
    assert voice.approved("- Spend approved: up to $3 for ElevenLabs")
    assert voice.approved("## Spend approved\n\nup to $3 for ElevenLabs narration\n")
    assert not voice.approved("- Spend approved: none")
    assert not voice.approved("- Spend approved: up to $20 for Kling clips")
    assert not voice.approved("ElevenLabs is nice")


def test_voice_live_path_writes_outputs_with_a_fake_post(tmp_path, monkeypatch):
    import base64
    (tmp_path / "narration.txt").write_text("Hello there\n\nSecond line\n")
    (tmp_path / "BRIEF.md").write_text("Spend approved: $1 ElevenLabs\n")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk-live-sentinel-999")
    text = "Hello there\n\nSecond line"
    n = len(text)
    alignment = {"characters": list(text), "character_start_times_seconds": [i * 0.1 for i in range(n)],
                 "character_end_times_seconds": [i * 0.1 + 0.1 for i in range(n)]}
    monkeypatch.setattr(voice, "post", lambda url, body, key: {"audio_base64": base64.b64encode(b"MP3").decode(), "alignment": alignment})
    assert voice.main(["--voice-id", "v1", "--project", str(tmp_path)]) == 0
    data = json.loads((tmp_path / "narration.sentences.json").read_text())
    assert data["characters"] == n and (tmp_path / "narration.mp3").read_bytes() == b"MP3"
    s = data["sentences"]
    assert s[0]["start"] == 0 and s[0]["end"] == round(10 * 0.1 + 0.1, 3) and s[1]["start"] == round(13 * 0.1, 3)
    assert f"characters={n}" in (tmp_path / "spend.log").read_text()
    assert "sk-live-sentinel-999" not in json.dumps(data) + (tmp_path / "spend.log").read_text()


# ---- 6 render_pipe disk guard ------------------------------------------------------------------------------
def test_space_guard_with_a_fake_low_value():
    assert render_pipe.space_ok(".", 500, free_fn=lambda p: 100.0) == (False, 100.0)
    assert render_pipe.space_ok(".", 500, free_fn=lambda p: 900.0) == (True, 900.0)
    assert render_pipe.space_ok(".", 500)[0] is True or render_pipe.free_mib(".") < 500   # the real call runs


# ---- 7 route R4 page renders a frame ---------------------------------------------------------------------------
def _chrome():
    return Path("/Applications/Google Chrome.app").exists() or shutil.which("google-chrome") or shutil.which("chromium")


@pytest.mark.skipif(not (shutil.which("uv") and shutil.which("npm") and _chrome()),
                    reason="needs uv, npm (network, to vendor three.js) and installed Chrome")
def test_page3d_renders_a_png(tmp_path):
    r = subprocess.run(["bash", str(SK / "scripts" / "vendor_three.sh"), str(tmp_path)], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"could not vendor three.js here: {r.stderr[-200:]}")
    shutil.copy(SK / "templates" / "page3d.html", tmp_path / "index.html")
    p = subprocess.run(["uv", "run", "--with", "playwright", "python", str(SK / "scripts" / "render_frames.py"), "--page", str(tmp_path / "index.html"),
                        "--stills", "1.5,9.9", "--out", str(tmp_path / "boards")], capture_output=True, text=True, cwd=tmp_path)
    if p.returncode != 0 and "playwright" in p.stderr.lower() and "install" in p.stderr.lower():
        pytest.skip("playwright browser support unavailable")
    assert p.returncode == 0, p.stderr[-500:]
    shots = sorted((tmp_path / "boards").glob("*.png"))
    assert len(shots) == 2 and all(s.stat().st_size > 5000 for s in shots)
    assert shots[0].read_bytes() != shots[1].read_bytes()                       # the scene changes with t
