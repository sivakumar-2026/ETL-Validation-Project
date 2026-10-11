"""Jenkins-friendly validation runner (no browser).

Writes:
  reports/validation_dashboard.html
  reports/validation_summary.json
  reports/db_fingerprint.json

Exit codes: 0 = all passed, 1 = test failures, 2 = runner error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fingerprint import (  # noqa: E402
    REPORT_DIR,
    capture_fingerprint,
    compare_with_previous,
    promote_previous,
    save_current,
)
from dashboard import reporter  # noqa: E402
from dashboard.render import render_html  # noqa: E402

HTML_PATH = REPORT_DIR / "validation_dashboard.html"
SUMMARY_PATH = REPORT_DIR / "validation_summary.json"


def main() -> int:
    import pytest

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    reporter.reset()

    db_changed = False
    fp: dict = {}
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

    HTML_PATH.write_text(render_html(report), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

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


if __name__ == "__main__":
    raise SystemExit(main())
