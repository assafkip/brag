#!/usr/bin/env python3
"""Copy rules for on-screen text and scripts.

  python3 copylint.py <file>... [--rulings rulings.json]

Rules (the founder's, from claudemy BRIEF.md and the global language rules):
  1. no emdash
  2. no double hyphen in visible text
  3. no banned phrases (AI-powered, leverage AI, cutting-edge, game-changing, revolutionary)
  4. project rules from rulings.json: "forbidden_words" and "forbidden_patterns" (regex)
  5. "allowed_phrases" in rulings.json: exact strings that exempt a forbidden word or pattern match
     when the match lies inside one of them (for example a labelled estimate such as "10x, founder's
     estimate" while bare multipliers stay forbidden). A variant of the phrase is not exempt.
  6. "no_final_period": true in rulings.json fails a sentence-final period, or a period after a digit that
     is not a decimal point, in the on-screen text of SCRIPT.md (the "## On-screen text" section), in
     narration.txt and in the visible text of HTML pages. File names (take1.mp3), decimals (3.5) and
     dotted names (index.html, example.test) are not flagged.

HTML files: only visible text is checked. <style>, <script>, comments and tag attributes are removed
first, so CSS variable names such as --ink never trip rule 2 (the one double-hyphen hit on the Sonos
cut was CSS variable syntax, not on-screen text). Markdown: fenced code blocks are skipped.
Exit 1 if anything is found.
"""
import argparse
import json
import re
import sys
from pathlib import Path

EMDASH = "—"
BANNED = ["AI-powered", "leverage AI", "cutting-edge", "game-changing", "revolutionary"]


def visible_text(path):
    raw = Path(path).read_text(errors="ignore")
    if str(path).lower().endswith((".html", ".htm")):
        ent = [e for e in ("&mdash;", "&#8212;", "&#x2014;") if e in raw]
        raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
        raw = re.sub(r"<(style|script)\b.*?</\1>", "", raw, flags=re.S | re.I)
        raw = re.sub(r"<[^>]+>", " ", raw)
        if ent:
            raw += "\n" + EMDASH + " (written as an HTML entity)"
        return raw
    return re.sub(r"```.*?```", "", raw, flags=re.S)


FINAL_PERIOD = re.compile(r"\.(?=\s|$|[\"')\]*_])")           # a period that ends something
AFTER_DIGIT = re.compile(r"(?<=\d)\.(?![\dA-Za-z])")           # digit, period, and not a decimal or a file extension


def _allowed_spans(line, allowed_phrases):
    spans = []
    for ph in allowed_phrases or ():
        if not ph:
            continue
        for m in re.finditer(re.escape(ph), line):
            spans.append((m.start(), m.end()))
    return spans


def _uncovered(line, pattern, spans, flags=0):
    """True if the pattern matches somewhere that no allowed phrase covers."""
    for m in re.finditer(pattern, line, flags):
        if not any(a <= m.start() and m.end() <= b for a, b in spans):
            return True
    return False


def lint_text(text, forbidden_words=(), forbidden_patterns=(), allowed_phrases=()):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        spans = _allowed_spans(line, allowed_phrases)
        if EMDASH in line:
            out.append((n, "emdash", line.strip()[:80]))
        if re.search(r"(?<!-)--(?!-)", line):
            out.append((n, "double hyphen", line.strip()[:80]))
        for b in BANNED:
            if b.lower() in line.lower():
                out.append((n, f"banned phrase '{b}'", line.strip()[:80]))
        for w in forbidden_words:
            if _uncovered(line, rf"\b{re.escape(w)}", spans, re.I):
                out.append((n, f"forbidden word '{w}'", line.strip()[:80]))
        for p in forbidden_patterns:
            if _uncovered(line, p, spans):
                out.append((n, f"forbidden pattern {p}", line.strip()[:80]))
    return out


def period_findings(text):
    """Sentence-final periods and periods after a number. [src: ...] tags are not copy and are ignored."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        body = re.sub(r"\[src:[^\]]*\]", "", line)
        if FINAL_PERIOD.search(body) or AFTER_DIGIT.search(body):
            out.append((n, "period after a sentence or number", line.strip()[:80]))
    return out


def onscreen_section(raw):
    """The lines of SCRIPT.md under '## On-screen text' only (Share copy and notes are not on screen)."""
    keep, on = [], False
    for line in raw.splitlines():
        if line.startswith("## "):
            on = line.lower().startswith("## on-screen text")
        elif on:
            keep.append(line)
    return "\n".join(keep)


def period_scope(path):
    """Text the no_final_period rule applies to for this file, or None if the file is out of scope."""
    name = Path(path).name.lower()
    raw = Path(path).read_text(errors="ignore")
    if name == "script.md":
        return onscreen_section(raw)
    if name == "narration.txt":
        return raw
    if name.endswith((".html", ".htm")):
        raw = re.sub(r"<!--.*?-->", "", raw, flags=re.S)
        raw = re.sub(r"<(style|script)\b.*?</\1>", "", raw, flags=re.S | re.I)
        return re.sub(r"<[^>]+>", "\n", raw)       # a tag boundary is a line boundary, so text never joins across tags
    return None


def lint_files(paths, rulings=None):
    rulings = rulings or {}
    res = {}
    for p in paths:
        found = lint_text(visible_text(p), rulings.get("forbidden_words", []), rulings.get("forbidden_patterns", []),
                          rulings.get("allowed_phrases", []))
        if rulings.get("no_final_period") is True:
            scope = period_scope(p)
            if scope is not None:
                found += period_findings(scope)
        res[str(p)] = found
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--rulings")
    a = ap.parse_args()
    rl = json.load(open(a.rulings)) if a.rulings else {}
    bad = 0
    for f, items in lint_files(a.files, rl).items():
        for n, rule, snip in items:
            bad += 1
            print(f"{f}:{n}: {rule}: {snip}")
    print(f"{bad} finding(s)")
    sys.exit(1 if bad else 0)
