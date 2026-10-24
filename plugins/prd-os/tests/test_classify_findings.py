"""Tests for plugins/prd-os/scripts/classify_findings.py.

Validates the substring-based classification rules used by the
planning-personas success metric.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from classify_findings import classify_body, classify_jsonl  # noqa: E402


def test_vague_goal_keyword_matches():
    body = "Success is not measurable; the metric is unclear."
    classes = classify_body(body)
    assert "vague-goal-class" in classes


def test_problem_clarity_matches_vague_goal():
    body = "Cites the rubric's Problem clarity dimension; no operationalized metric."
    assert "vague-goal-class" in classify_body(body)


def test_empty_non_goals_keyword_matches():
    body = "The non-goals section is empty so scope creep is unconstrained."
    classes = classify_body(body)
    assert "empty-non-goals-class" in classes


def test_unbounded_scope_matches_empty_non_goals():
    body = "Risk: scope creep because non-goals are not stated."
    classes = classify_body(body)
    assert "empty-non-goals-class" in classes


def test_both_classes_match_on_one_body():
    body = "Vague goal: no metric. Plus scope creep risk because non-goals missing."
    classes = classify_body(body)
    assert "vague-goal-class" in classes
    assert "empty-non-goals-class" in classes


def test_other_when_no_keywords_match():
    body = "Minor wording nit on the rollback paragraph."
    assert classify_body(body) == set()


def test_non_string_body_returns_empty():
    assert classify_body(None) == set()
    assert classify_body(123) == set()


def test_case_insensitive():
    body = "VAGUE goal language; no METRIC"
    assert "vague-goal-class" in classify_body(body)


def test_classify_jsonl_file(tmp_path):
    findings_file = tmp_path / "demo-findings.jsonl"
    records = [
        {"id": "finding-1", "severity": "major", "body": "Goals are vague and not measurable."},
        {"id": "finding-2", "severity": "minor", "body": "Wording nit on rollback paragraph."},
        {"id": "finding-3", "severity": "major", "body": "Non-goals section is empty, scope creep risk."},
        {"id": "finding-4", "severity": "blocker", "body": "Manifest entry missing required keys."},
    ]
    findings_file.write_text("\n".join(json.dumps(r) for r in records))

    counts = classify_jsonl(findings_file)
    assert counts["total"] == 4
    assert counts["vague-goal-class"] == 1
    assert counts["empty-non-goals-class"] == 1
    assert counts["other"] == 2


def test_classify_jsonl_missing_file(tmp_path):
    counts = classify_jsonl(tmp_path / "does-not-exist.jsonl")
    assert counts == {"vague-goal-class": 0, "empty-non-goals-class": 0, "other": 0, "total": 0}


def test_classify_jsonl_skips_bad_lines(tmp_path):
    findings_file = tmp_path / "messy-findings.jsonl"
    findings_file.write_text('{"body":"vague goal"}\nnot-json\n{"body":"non-goals empty"}\n')
    counts = classify_jsonl(findings_file)
    assert counts["total"] == 2
    assert counts["vague-goal-class"] == 1
    assert counts["empty-non-goals-class"] == 1
