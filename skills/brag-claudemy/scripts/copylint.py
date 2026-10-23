#!/usr/bin/env python3
"""Copy rules for on-screen text and scripts.

  python3 copylint.py <file>... [--rulings rulings.json]

Rules (the founder's, from claudemy BRIEF.md and the global language rules):
  1. no emdash
  2. no double hyphen in visible text
  3. no banned phrases (AI-powered, leverage AI, cutting-edge, game-changing, revolutionary)
  4. project rules from rulings.json: "forbidden_words" and "forbidden_patterns" (regex)

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


def lint_text(text, forbidden_words=(), forbidden_patterns=()):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        if EMDASH in line:
            out.append((n, "emdash", line.strip()[:80]))
        if re.search(r"(?<!-)--(?!-)", line):
            out.append((n, "double hyphen", line.strip()[:80]))
        for b in BANNED:
            if b.lower() in line.lower():
                out.append((n, f"banned phrase '{b}'", line.strip()[:80]))
        for w in forbidden_words:
            if re.search(rf"\b{re.escape(w)}", line, re.I):
                out.append((n, f"forbidden word '{w}'", line.strip()[:80]))
        for p in forbidden_patterns:
            if re.search(p, line):
                out.append((n, f"forbidden pattern {p}", line.strip()[:80]))
    return out


def lint_files(paths, rulings=None):
    rulings = rulings or {}
    res = {}
    for p in paths:
        res[str(p)] = lint_text(visible_text(p), rulings.get("forbidden_words", []), rulings.get("forbidden_patterns", []))
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
