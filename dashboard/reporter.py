"""Pytest plugin: collect status, logs, duration, and sample rows."""

from __future__ import annotations

import pytest

from dashboard.samples import extract_samples
from dashboard.timeutil import now_ist_label

_results: list[dict] = []
_started_at: str | None = None


def reset() -> None:
    global _results, _started_at
    _results = []
    _started_at = now_ist_label()


def collected() -> dict:
    passed = sum(1 for r in _results if r["status"] == "passed")
    failed = sum(1 for r in _results if r["status"] == "failed")
    skipped = sum(1 for r in _results if r["status"] == "skipped")
    return {
        "generated_at": now_ist_label(),
        "started_at": _started_at,
        "totals": {
            "total": len(_results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        },
        "tests": _results,
    }


def pytest_configure(config):
    reset()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.when == "teardown":
        return
    if report.when == "setup" and not report.failed and not report.skipped:
        return
    if any(r["nodeid"] == item.nodeid for r in _results):
        return

    status = "passed"
    if report.failed:
        status = "failed"
    elif report.skipped:
        status = "skipped"

    log_parts = []
    if report.skipped:
        skip_reason = ""
        if isinstance(report.longrepr, tuple) and len(report.longrepr) >= 3:
            skip_reason = str(report.longrepr[2])
        log_parts.append(skip_reason or "Skipped")
    elif report.passed:
        log_parts.append("Passed")
    elif report.failed:
        # Keep assertion text short; detail is in failure-item tables
        msg = str(report.longreprtext if hasattr(report, "longreprtext") else report.longrepr)
        lines = [ln for ln in msg.splitlines() if ln.strip()]
        log_parts.append("\n".join(lines[-8:]) if lines else "Failed")

    samples = {}
    try:
        samples = extract_samples(item, status=status)
    except Exception as exc:
        if status == "failed":
            samples = {
                "Failure items — Value mismatch": {
                    "columns": ["note"],
                    "rows": [[f"Could not build failure tables: {exc}"]],
                }
            }

    title = item.name
    cls = item.getparent(pytest.Class)
    suite = cls.name if cls is not None else (item.module.__name__ if item.module else "tests")

    _results.append(
        {
            "nodeid": item.nodeid,
            "suite": suite,
            "name": title,
            "status": status,
            "duration_s": round(getattr(report, "duration", 0.0) or 0.0, 4),
            "log": "\n\n".join(p for p in log_parts if p),
            "samples": samples,
        }
    )
