"""Self-contained regression test for the issues_dir default.

With NO `.prd-os/config.json`, issue_runner must resolve issues_dir to
`.prd-os/issues` — the same default config.py (and prd-os/prd_split) use.
Previously DEFAULT_ISSUES_DIR was `issues`, so a no-config repo wrote specs to
`.prd-os/issues` (via config/prd_split) while this runner looked under
`./issues`, and `load` failed.

Run: python3 test_issue_dir_default.py   (also discoverable by pytest)
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RUNNER = Path(__file__).resolve().parent / "issue_runner.py"

_MARKER = (
    "<!-- generated-by: prd_split.py prd=prd-fixture finding=finding-fixture "
    "at=2026-04-20T00:00:00Z -->"
)

_SPEC = f"""\
---
id: align-check
title: align-check fixture
status: open
priority: p0
allowed_files:
  - src/x.py
disallowed_files: []
required_checks: []
required_reviews: []
---
{_MARKER}

Fixture spec.
"""


def test_default_issues_dir_is_prd_os_issues():
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d)
        (repo / ".git").mkdir()
        # No config.json. Spec lives at the canonical default location.
        issues = repo / ".prd-os" / "issues"
        issues.mkdir(parents=True)
        (issues / "align-check.md").write_text(_SPEC)

        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(repo)
        r = subprocess.run(
            [sys.executable, str(RUNNER), "load", "align-check"],
            cwd=str(repo), capture_output=True, text=True, env=env,
        )
        assert r.returncode == 0, r.stderr
        assert json.loads(r.stdout)["loaded"] == "align-check"


if __name__ == "__main__":
    test_default_issues_dir_is_prd_os_issues()
    print("ok")
