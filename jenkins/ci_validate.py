"""Jenkins/CI validation runner (no browser).

Always writes reports/validation_summary.json when possible.
Exit codes: 0 = all passed, 1 = test failures, 2 = runner error
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

REPORT_DIR = ROOT / "reports"
HTML_PATH = REPORT_DIR / "validation_dashboard.html"
SUMMARY_PATH = REPORT_DIR / "validation_summary.json"


def _write_report(report: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        from dashboard.render import render_html

        HTML_PATH.write_text(render_html(report), encoding="utf-8")
    except Exception as exc:
        HTML_PATH.write_text(
            f"<html><body><pre>HTML render failed: {exc}\n\n{json.dumps(report, indent=2)}</pre></body></html>",
            encoding="utf-8",
        )
    SUMMARY_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> int:
    try:
        from fingerprint import (
            capture_fingerprint,
            compare_with_previous,
            promote_previous,
            save_current,
        )
        from dashboard import reporter
        from dashboard.timeutil import now_ist_label
        import pytest
    except Exception as exc:
        report = {
            "generated_at": "",
            "totals": {"total": 0, "passed": 0, "failed": 1, "skipped": 0},
            "tests": [
                {
                    "nodeid": "ci_validate",
                    "suite": "runner",
                    "name": "import_error",
                    "status": "failed",
                    "duration_s": 0,
                    "log": f"{exc}\n{traceback.format_exc()}",
                    "samples": {},
                }
            ],
            "db_fingerprint": {},
            "db_changed": False,
            "error": str(exc),
        }
        _write_report(report)
        print(f"CI_VALIDATE_IMPORT_ERROR={exc}")
        return 2

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    reporter.reset()

    db_changed = False
    fp: dict = {}
    code = 2

    try:
        try:
            fp = capture_fingerprint()
            db_changed = compare_with_previous(fp)
            save_current(fp)
        except Exception as exc:
            fp = {"error": str(exc)}

        code = pytest.main(
            [
                str(ROOT),
                "-q",
                "--tb=short",
                "-p",
                "dashboard.reporter",
                "--ignore=dashboard",
                "--ignore=jenkins",
                "--ignore=run_dashboard.py",
            ]
        )

        report = reporter.collected()
        report["db_fingerprint"] = fp
        report["db_changed"] = db_changed
        report["jenkins"] = True
        _write_report(report)

        if "error" not in fp:
            promote_previous(fp)

        totals = report["totals"]
        print(
            f"TOTAL={totals['total']} PASSED={totals['passed']} "
            f"FAILED={totals['failed']} SKIPPED={totals['skipped']} "
            f"DB_CHANGED={db_changed}"
        )
        print(f"HTML={HTML_PATH}")
        print(f"SUMMARY={SUMMARY_PATH}")

        if code not in (0, 1):
            return 2
        return 0 if code == 0 else 1

    except Exception as exc:
        report = {
            "generated_at": now_ist_label(),
            "started_at": now_ist_label(),
            "totals": {"total": 0, "passed": 0, "failed": 1, "skipped": 0},
            "tests": [
                {
                    "nodeid": "ci_validate",
                    "suite": "runner",
                    "name": "ci_validate_crash",
                    "status": "failed",
                    "duration_s": 0,
                    "log": f"{exc}\n{traceback.format_exc()}",
                    "samples": {},
                }
            ],
            "db_fingerprint": fp,
            "db_changed": db_changed,
            "jenkins": True,
            "error": str(exc),
        }
        try:
            _write_report(report)
        except Exception:
            SUMMARY_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"CI_VALIDATE_ERROR={exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
