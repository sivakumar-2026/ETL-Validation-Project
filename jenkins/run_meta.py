"""Resolve run type for subject line / email metadata."""

from __future__ import annotations

import json
import os
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"
SUMMARY = REPORT_DIR / "validation_summary.json"
META = REPORT_DIR / "run_meta.json"

# Priority: explicit RUN_TYPE > CI Push > Daily RUN > Automatic (fingerprint) > Manual
RUN_CI = "CI Push"
RUN_AUTOMATIC = "Automatic Validation"
RUN_DAILY = "Daily RUN"
RUN_MANUAL = "Manual"


def resolve_run_type(db_changed: bool | None = None) -> str:
    explicit = os.getenv("RUN_TYPE", "").strip()
    if explicit:
        return explicit

    # GitHub Actions / CI
    if os.getenv("GITHUB_ACTIONS", "").lower() == "true":
        return RUN_CI
    if os.getenv("CI", "").strip() in {"1", "true", "TRUE"}:
        return RUN_CI

    if db_changed is None and SUMMARY.exists():
        db_changed = bool(json.loads(SUMMARY.read_text(encoding="utf-8")).get("db_changed"))

    # Jenkins timer / explicit daily flag
    if os.getenv("DAILY_RUN", "").strip() in {"1", "true", "TRUE", "yes"}:
        return RUN_DAILY
    if os.getenv("BUILD_CAUSE", "").find("Timer") >= 0:
        return RUN_DAILY
    causes = os.getenv("BUILD_CAUSE_JSON", "") + os.getenv("HUDSON_SERVER_COOKIE", "")
    if "TimerTrigger" in os.getenv("BUILD_CAUSES", "") or "hudson.triggers.TimerTrigger" in causes:
        return RUN_DAILY

    if db_changed:
        return RUN_AUTOMATIC

    return RUN_MANUAL


def subject_for(run_type: str, failed: int) -> str:
    status = "FAILED" if failed else "PASSED"
    return f"ETL QA Validation Report - {run_type} ({status})"


def write_meta(run_type: str | None = None) -> dict:
    data = {}
    if SUMMARY.exists():
        data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    db_changed = bool(data.get("db_changed"))
    failed = int(data.get("totals", {}).get("failed", 0))
    run_type = run_type or resolve_run_type(db_changed)
    meta = {
        "run_type": run_type,
        "subject": subject_for(run_type, failed),
        "db_changed": db_changed,
        "failed": failed,
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    META.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return meta
