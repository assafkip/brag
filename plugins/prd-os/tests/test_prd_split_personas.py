"""Test that prd_split.py correctly parses PRDs containing a `## Persona Review` section.

The planning-personas experiment inserts a new `## Persona Review` section
immediately before `## Issues` in the PRD spec. This test confirms that:
  1. prd_split.py finds and parses the `## Issues` JSON block correctly
     even when a `## Persona Review` section precedes it.
  2. The presence of the Persona Review section does not cause spurious
     issues to be emitted.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from prd_split import _extract_issues_block, _parse_frontmatter, _validate_manifest  # noqa: E402


def _parse_issues_from_text(text: str) -> list[dict]:
    """Helper: drive the prd_split parsing flow on raw PRD text."""
    _, body_offset = _parse_frontmatter(text)
    body = text[body_offset:]
    raw = _extract_issues_block(body)
    return _validate_manifest(raw)


PRD_WITH_PERSONA_REVIEW = """---
id: prd-test-personas-2026-05-14
title: Test PRD with Persona Review
status: approved
created_at: 2026-05-14
updated_at: 2026-05-14
owner: test
reviewers: []
findings_path: .prd-os/findings/prd-test-personas-2026-05-14-findings.jsonl
codex_reviewed_at: 2026-05-14T10:00:00Z
---

# Test PRD with Persona Review

## Problem

Test problem statement.

## Goals

- One goal.

## Non-goals

- One non-goal.

## Proposed approach

Test approach.

## Risks and rollback

Test risks.

## Open questions

- One question.

## Persona Review

### Skeptic

**Q1: What is the strongest argument against doing this?**
A1: Test answer one.

**Q2: What is the smallest experiment that would disprove the thesis?**
A2: Test answer two.

**Q3: What is the cheapest non-build alternative?**
A3: Test answer three.

## Issues

```json
[
  {
    "id": "test-issue-one",
    "title": "Test issue one",
    "finding_id": "finding-1",
    "allowed_files": ["test.py"],
    "required_checks": ["pytest test.py"]
  }
]
```
"""


PRD_WITHOUT_PERSONA_REVIEW = """---
id: prd-test-no-personas-2026-05-14
title: Test PRD without Persona Review
status: approved
codex_reviewed_at: 2026-05-14T10:00:00Z
---

## Issues

```json
[
  {
    "id": "test-issue-only",
    "title": "Only issue",
    "finding_id": "finding-1",
    "allowed_files": ["test.py"],
    "required_checks": ["pytest test.py"]
  }
]
```
"""


def test_persona_review_section_does_not_break_issues_parsing(tmp_path):
    prd_file = tmp_path / "prd.md"
    prd_file.write_text(PRD_WITH_PERSONA_REVIEW)
    text = prd_file.read_text()
    issues = _parse_issues_from_text(text)
    assert len(issues) == 1
    assert issues[0]["id"] == "test-issue-one"
    assert issues[0]["finding_id"] == "finding-1"


def test_persona_review_content_does_not_become_an_issue(tmp_path):
    prd_file = tmp_path / "prd.md"
    prd_file.write_text(PRD_WITH_PERSONA_REVIEW)
    text = prd_file.read_text()
    block = _extract_issues_block(text)
    assert "## Persona Review" not in block
    assert "Skeptic" not in block
    issues = _validate_manifest(block)
    titles = [i["title"] for i in issues]
    assert "Skeptic" not in " ".join(titles)


def test_baseline_no_persona_review_still_parses(tmp_path):
    prd_file = tmp_path / "prd.md"
    prd_file.write_text(PRD_WITHOUT_PERSONA_REVIEW)
    text = prd_file.read_text()
    issues = _parse_issues_from_text(text)
    assert len(issues) == 1
    assert issues[0]["id"] == "test-issue-only"


def test_persona_review_rerun_subsection_does_not_break_parsing(tmp_path):
    prd_text = PRD_WITH_PERSONA_REVIEW.replace(
        "### Skeptic\n\n",
        "### Skeptic\n\nFirst run content.\n\n### Skeptic (rerun 2026-05-15T12:00:00Z)\n\nSecond run content.\n\n",
    )
    prd_file = tmp_path / "prd.md"
    prd_file.write_text(prd_text)
    text = prd_file.read_text()
    issues = _parse_issues_from_text(text)
    assert len(issues) == 1
    assert issues[0]["id"] == "test-issue-one"

def test_persona_answer_containing_issues_heading_corrupts_parser(tmp_path):
    """If a founder's persona answer contains a level-2 ## Issues heading,
    _extract_issues_block anchors on the wrong heading and parses garbage.

    This test documents the failure mode that the /prd-personas command
    sanitization step is designed to prevent at write time. The parser
    itself does not (and should not) defend against this; the command
    must reject the answer before persisting it.
    """
    corrupt_prd = PRD_WITH_PERSONA_REVIEW.replace(
        "**Q1: What is the strongest argument against doing this?**\nA1: Test answer one.",
        "**Q1: What is the strongest argument against doing this?**\nA1: Look at the issues section.\n\n## Issues\n\n```json\n[{\"id\": \"injected\"}]\n```\n",
    )
    prd_file = tmp_path / "corrupt.md"
    prd_file.write_text(corrupt_prd)
    text = prd_file.read_text()
    _, body_offset = _parse_frontmatter(text)
    body = text[body_offset:]
    block = _extract_issues_block(body)
    # Parser anchors on the FIRST ## Issues heading, which is now inside the answer
    assert "injected" in block
    # This is why the command must sanitize answers before writing them

