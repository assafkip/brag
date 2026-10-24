#!/usr/bin/env python3
"""Project-file checks adapted from a design-chain method (see references/method.md, "Lessons from the design chain").

Each function reads files in the project folder and returns (status, detail), status one of
PASS, FAIL, WARN, INFO. verify.py prints them. They check that the step was DONE and that its claims line
up with each other; none of them says the video is good (rulings.md, ruling 25).

  study_check      STUDY.md exists and cites at least MIN_TECHNIQUES techniques, each with a time
  craft_check      craft.json techniques cite a time that STUDY.md contains, and their fingerprints are in index.html
  directions_check DIRECTIONS.md names three directions (or says it implements an approved pick)
  vision_check     BRIEF.md carries the person's own words, quoted, under a Vision heading
  critique_check   every WEAK[tag] in CRITIQUE.md has a DISPOSITION[tag] line
  readers_check    readers.jsonl rows for THIS video, no LEAVE, at least rulings.json "readers_required" readers,
                   and each row's retell coverage (retell_matched out of retell_total narration lines)

A missing file is WARN for the steps the method requires (study, craft, directions, vision) and INFO for
opt-in ones (critique, readers). A gate that is red on every older project gets switched off, so a new
check starts as a warning where the file does not exist yet; once the file exists, its problems are FAIL.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

MIN_TECHNIQUES = 12
TIME_CITE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:s|sec|secs|seconds)\b|\b\d{1,2}:\d{2}\b|\b\d+(?:\.\d+)?\s*to\s*\d+(?:\.\d+)?\s*s\b", re.I)
ITEM = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+(.*)$")


def _read(p):
    return Path(p).read_text(errors="ignore") if Path(p).exists() else None


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def section(raw, title_re):
    """Lines under the first '## ' heading whose title matches title_re, up to the next '## ' heading."""
    out, on = [], False
    for line in raw.splitlines():
        if line.startswith("## "):
            on = bool(re.search(title_re, line[3:], re.I))
        elif on:
            out.append(line)
    return out


def cited_techniques(raw):
    """List items under the Techniques section that cite a time. Lines still holding a {{placeholder}} do not count."""
    items = []
    for line in section(raw, r"technique"):
        m = ITEM.match(line)
        if m and "{{" not in m.group(1) and TIME_CITE.search(m.group(1)):
            items.append(m.group(1).strip())
    return items


def study_check(proj):
    raw = _read(Path(proj) / "STUDY.md")
    if raw is None:
        return "WARN", f"STUDY.md missing: study the reference before designing (templates/STUDY.md); a build from memory copies its grammar and not its production"
    n = len(cited_techniques(raw))
    notes = []
    ref = _read(Path(proj) / "reference.json")
    if ref:
        try:
            names = json.loads(ref).get("references") or []
        except ValueError:
            names = []
        absent = [x for x in names if str(x).lower() not in raw.lower()]
        if absent:
            notes.append(f"reference(s) in reference.json not named in STUDY.md: {absent} (a new reference changes what the others mean, so re-read the set)")
    if n < MIN_TECHNIQUES:
        notes.insert(0, f"{n} cited technique(s), at least {MIN_TECHNIQUES} wanted")
    if notes:
        return "WARN", "; ".join(notes)
    return "PASS", f"{n} cited techniques"


def _page_source(proj):
    page = Path(proj) / "index.html"
    if not page.exists():
        return None
    src = page.read_text(errors="ignore")
    src = re.sub(r"<!--.*?-->", " ", src, flags=re.S)
    return re.sub(r"/\*.*?\*/", " ", src, flags=re.S)


def craft_check(proj):
    p = Path(proj) / "craft.json"
    if not p.exists():
        return "WARN", "craft.json missing: list the techniques taken from STUDY.md with a fingerprint each (templates/craft.json)"
    try:
        man = json.loads(p.read_text())
    except ValueError as e:
        return "FAIL", f"craft.json is not valid JSON: {e}"
    techs = man.get("techniques") or []
    if not techs:
        return "FAIL", "craft.json declares no techniques, so nothing was verified; declaring nothing must not be the cheapest way to comply"
    study = _read(Path(proj) / "STUDY.md") or ""
    src = _page_source(proj)
    probs = []
    for t in techs:
        tid = t.get("id", "?")
        ref = str(t.get("reference", "")).strip()
        if not ref:
            probs.append(f"{tid}: cites no reference (a technique with no source is invention)")
        elif ref.lower() not in study.lower():
            probs.append(f"{tid}: reference '{ref}' is not in STUDY.md")
        fps = t.get("fingerprint") or []
        if not fps:
            probs.append(f"{tid}: declares no fingerprint, so it cannot be verified present")
        elif src is None:
            probs.append(f"{tid}: index.html not found to check the fingerprint against")
        else:
            miss = []
            for f in fps:
                try:
                    if not re.search(f, src):
                        miss.append(f)
                except re.error:
                    miss.append(f + " (bad regex)")
            if miss:
                probs.append(f"{tid}: declared but absent from index.html: {miss}")
    if probs:
        return "FAIL", "; ".join(probs[:4]) + (f"; +{len(probs) - 4} more" if len(probs) > 4 else "")
    return "PASS", f"{len(techs)} technique(s) cite STUDY.md and appear in index.html"


def directions_check(proj):
    raw = _read(Path(proj) / "DIRECTIONS.md")
    if raw is None:
        return "WARN", "DIRECTIONS.md missing: write three directions and get a pick before building (templates/DIRECTIONS.md)"
    if re.search(r"^Implements:\s*\S", raw, re.M):
        return "PASS", "builds an approved pick (Implements line)"
    heads = [l for l in raw.splitlines() if re.match(r"^#{2,3}\s+\S", l) and "{{" not in l]
    if len(heads) < 3:
        return "WARN", f"DIRECTIONS.md names {len(heads)} direction heading(s); three are wanted unless it has an 'Implements:' line"
    return "PASS", f"{len(heads)} directions"


def vision_check(proj):
    raw = _read(Path(proj) / "BRIEF.md")
    if raw is None:
        return "WARN", "BRIEF.md missing"
    quotes = [l for l in section(raw, r"vision") if l.strip().startswith(">") and len(l.strip(" >")) > 20 and "{{" not in l]
    if not quotes:
        return "WARN", "BRIEF.md has no quoted line (starting with '>') under '## Vision': the aim is the person's own words, not the builder's"
    return "PASS", f"{len(quotes)} quoted vision line(s)"


def critique_check(proj):
    raw = _read(Path(proj) / "CRITIQUE.md")
    if raw is None:
        return "INFO", "no CRITIQUE.md (opt-in: mark each weakness WEAK[tag] and answer it with DISPOSITION[tag])"
    weak = set(re.findall(r"WEAK\[([\w-]+)\]", raw))
    done = set(re.findall(r"DISPOSITION\[([\w-]+)\]\s*:\s*\S", raw))
    open_ = sorted(weak - done)
    if open_:
        return "FAIL", f"weakness without a disposition: {open_}"
    return "PASS", f"{len(weak)} weakness(es), each with a disposition"


def retell_coverage(rows):
    """(matched, total, rows missing the pair, rows whose pair is impossible) over reader rows.

    Why the check reads this: five readers shown silent contact sheets of the openwitness cut
    retold the whole story correctly and still said LEAVE, mostly "leans on the narration" or
    "product arrives late" -- the narration carried the beat they said was missing. The retell is
    the useful instrument; a STAY or LEAVE verdict reached without the audio is not (ASK-3036).
    So each row records how many narration lines the reader's retell covered, next to the verdict.
    """
    matched = total = 0
    missing, impossible = [], []
    for r in rows:
        who = str(r.get("reader"))
        m, t = r.get("retell_matched"), r.get("retell_total")
        if m is None or t is None:
            missing.append(who)
            continue
        if not isinstance(m, int) or not isinstance(t, int) or t <= 0 or not 0 <= m <= t:
            impossible.append(f"{who} ({m} of {t})")
            continue
        matched, total = matched + m, total + t
    return matched, total, sorted(set(missing)), sorted(set(impossible))


def readers_check(proj, video=None):
    rl = {}
    if (Path(proj) / "rulings.json").exists():
        try:
            rl = json.loads((Path(proj) / "rulings.json").read_text())
        except ValueError:
            rl = {}
    need = rl.get("readers_required")
    if not need:
        return "INFO", "no readers_required in rulings.json (opt-in: independent readers who saw only the video)"
    rows_file = Path(proj) / "readers.jsonl"
    rows = []
    for line in (rows_file.read_text().splitlines() if rows_file.exists() else []):
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                return "FAIL", "readers.jsonl holds a line that is not JSON"
    sha = sha256(video) if video and Path(video).exists() else None
    mine = [r for r in rows if isinstance(r, dict) and (sha is None or r.get("video_sha256") == sha)]
    ids = {r.get("reader") for r in mine if r.get("verdict") in ("STAY", "LEAVE")}
    if any(r.get("verdict") == "LEAVE" for r in mine):
        who = sorted({str(r.get("reader")) for r in mine if r.get("verdict") == "LEAVE"})
        return "FAIL", f"reader(s) {who} would leave"
    if len(ids) < int(need):
        return "FAIL", f"{len(ids)} reader(s) on this exact video, {need} required (rows for an older render do not count)"
    judged = [r for r in mine if r.get("verdict") in ("STAY", "LEAVE")]
    matched, total, missing, impossible = retell_coverage(judged)
    if impossible:
        return "FAIL", f"retell coverage is not a count of narration lines matched out of the total: {impossible}"
    cover = f"retell coverage {matched}/{total}" if total else "no retell coverage recorded"
    if missing:
        return "WARN", (f"{len(ids)} independent reader(s), none would leave; {cover}, but reader(s) {missing} record no"
                        " retell coverage, so their verdict was reached without the narration (references/reader-brief.md)")
    return "PASS", f"{len(ids)} independent reader(s), none would leave; {cover}"


def run_all(proj, video=None):
    return [("study", *study_check(proj)), ("craft", *craft_check(proj)), ("directions", *directions_check(proj)),
            ("vision", *vision_check(proj)), ("critique", *critique_check(proj)), ("readers", *readers_check(proj, video))]


if __name__ == "__main__":
    for n, s, d in run_all(sys.argv[1] if len(sys.argv) > 1 else "."):
        print(f"{n:<10} {s:<5} {d}")
