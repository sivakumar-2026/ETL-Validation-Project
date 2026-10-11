"""Build clean email body + subject from validation_summary.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from run_meta import subject_for, write_meta  # noqa: E402
from dashboard.timeutil import now_ist_label  # noqa: E402

REPORT_DIR = ROOT / "reports"
SUMMARY = REPORT_DIR / "validation_summary.json"
BODY = REPORT_DIR / "email_body.txt"
SUBJECT = REPORT_DIR / "email_subject.txt"


def _table_block(title: str, table: dict) -> list[str]:
    lines = ["", title, "-" * len(title)]
    cols = table.get("columns") or []
    rows = table.get("rows") or []
    lines.append(" | ".join(cols))
    lines.append("-" * max(20, len(lines[-1])))
    for row in rows[:50]:
        lines.append(" | ".join(str(c) for c in row))
    return lines


def _pick_failure_tables(failed_tests: list[dict]) -> dict:
    for t in failed_tests:
        samples = t.get("samples") or {}
        if any(k.startswith("Failure items") for k in samples):
            return samples
    return {}


def build_from_summary(data: dict) -> tuple[str, str, int]:
    t = data.get("totals", {})
    failed = [x for x in data.get("tests", []) if x.get("status") == "failed"]
    fp = data.get("db_fingerprint", {})
    meta = write_meta()
    run_type = meta["run_type"]
    fail_n = int(t.get("failed", 0))

    lines = [
        "ETL QA Validation Report",
        "=" * 40,
        f"Run type : {run_type}",
        f"Generated: {data.get('generated_at', now_ist_label())}",
        f"Total    : {t.get('total', 0)}",
        f"Pass     : {t.get('passed', 0)}",
        f"Fail     : {fail_n}",
        f"Skip     : {t.get('skipped', 0)}",
        "",
        "Source: "
        f"{fp.get('source', {}).get('table')} | rows={fp.get('source', {}).get('count')} | "
        f"max_pk={fp.get('source', {}).get('max_pk')}",
        "Target: "
        f"{fp.get('target', {}).get('table')} | rows={fp.get('target', {}).get('count')} | "
        f"max_pk={fp.get('target', {}).get('max_pk')}",
    ]

    if fp.get("error"):
        lines += ["", f"Fingerprint/DB error: {fp.get('error')}"]

    if failed:
        lines += ["", "Failed tests", "-" * 12]
        for f in failed:
            lines.append(f"• {f.get('suite')}.{f.get('name')}")

        tables = _pick_failure_tables(failed)
        if tables:
            lines += ["", "Failure details (once)"]
            for title in (
                "Failure items — Only in TARGET",
                "Failure items — Only in SOURCE",
                "Failure items — Value mismatch",
            ):
                if title in tables:
                    lines += _table_block(title, tables[title])
    else:
        lines += ["", "All tests passed." if fail_n == 0 else "No per-test failure details available."]

    lines += ["", "PDF report attached when available: validation_report.pdf"]
    return "\n".join(lines), meta["subject"], fail_n


def build_error_body(message: str) -> tuple[str, str]:
    run_type = write_meta().get("run_type", "CI Push")
    subject = subject_for(run_type, failed=1)
    body = "\n".join(
        [
            "ETL QA Validation Report",
            "=" * 40,
            f"Run type : {run_type}",
            f"Generated: {now_ist_label()}",
            "",
            "Validation could not produce a full summary.",
            f"Detail: {message}",
            "",
            "Check the GitHub Actions log for the Validate step.",
        ]
    )
    return body, subject


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if not SUMMARY.exists():
        body, subject = build_error_body("validation_summary.json was not created")
        BODY.write_text(body, encoding="utf-8")
        SUBJECT.write_text(subject, encoding="utf-8")
        print(body)
        print(f"\nSUBJECT={subject}")
        print(f"EMAIL_BODY={BODY}")
        return 1

    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    text, subject, fail_n = build_from_summary(data)
    BODY.write_text(text, encoding="utf-8")
    SUBJECT.write_text(subject, encoding="utf-8")
    print(text)
    print(f"\nSUBJECT={subject}")
    print(f"EMAIL_BODY={BODY}")
    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
