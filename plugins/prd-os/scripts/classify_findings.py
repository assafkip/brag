#!/usr/bin/env python3
"""Classify Codex findings into vague-goal-class and empty-non-goals-class buckets.

Used by the prd-os planning-personas experiment to measure the rate of these
two finding classes across PRDs that did and did not run the persona session.

Classification is body-text based (substring search, case-insensitive). The
keyword lists are pinned in this file. Changing them changes how findings
classify, which changes the baseline-vs-personas comparison; pin the lists
deliberately and document any change in the prd-personas-baseline.md file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


VAGUE_GOAL_KEYWORDS = (
    "vague",
    "not measurable",
    "unclear what success",
    "no metric",
    "operationalized",
    "outcome-focused",
    "implementation-focused",
    "problem clarity",
)

EMPTY_NON_GOALS_KEYWORDS = (
    "non-goals",
    "scope creep",
    "scope discipline",
    "unbounded scope",
)


def classify_body(body: str) -> set[str]:
    """Return the set of classes a finding body matches."""
    if not isinstance(body, str):
        return set()
    text = body.lower()
    classes: set[str] = set()
    for kw in VAGUE_GOAL_KEYWORDS:
        if kw in text:
            classes.add("vague-goal-class")
            break
    for kw in EMPTY_NON_GOALS_KEYWORDS:
        if kw in text:
            classes.add("empty-non-goals-class")
            break
    return classes


def classify_jsonl(path: Path) -> dict:
    """Walk a findings JSONL file and return per-class counts."""
    counts = {"vague-goal-class": 0, "empty-non-goals-class": 0, "other": 0, "total": 0}
    if not path.is_file():
        return counts
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        body = rec.get("body", "")
        classes = classify_body(body)
        counts["total"] += 1
        if not classes:
            counts["other"] += 1
            continue
        for cls in classes:
            counts[cls] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_one = sub.add_parser("file", help="Classify a single findings JSONL file")
    p_one.add_argument("path", help="Path to <prd-id>-findings.jsonl")

    p_dir = sub.add_parser("dir", help="Classify every JSONL file under a directory")
    p_dir.add_argument("path", help="Directory containing findings files")

    args = parser.parse_args()

    if args.cmd == "file":
        counts = classify_jsonl(Path(args.path))
        json.dump(counts, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    if args.cmd == "dir":
        root = Path(args.path)
        if not root.is_dir():
            print(f"not a directory: {root}", file=sys.stderr)
            return 2
        aggregate = {"vague-goal-class": 0, "empty-non-goals-class": 0, "other": 0, "total": 0}
        per_file = {}
        for path in sorted(root.glob("*-findings.jsonl")):
            counts = classify_jsonl(path)
            per_file[path.name] = counts
            for k, v in counts.items():
                aggregate[k] += v
        out = {"aggregate": aggregate, "per_file": per_file}
        json.dump(out, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
