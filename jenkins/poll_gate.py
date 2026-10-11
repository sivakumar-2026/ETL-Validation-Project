"""Jenkins poll gate: decide whether to run full validation.

Exit codes:
  0 = run full validation + email
  3 = no DB change — skip validation (poll only)
  2 = error reading DBs

Writes reports/poll_gate.json with decision details.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fingerprint import (  # noqa: E402
    GATE_PATH,
    REPORT_DIR,
    capture_fingerprint,
    compare_with_previous,
    save_current,
)

IST = ZoneInfo("Asia/Kolkata")


def _is_daily_window() -> bool:
    """True for the scheduled Daily RUN slot (10:00–10:14 IST)."""
    if os.getenv("DAILY_RUN", "").strip() in {"1", "true", "TRUE", "yes"}:
        return True
    if os.getenv("FORCE_FULL", "").strip() in {"1", "true", "TRUE", "yes"}:
        return True
    now = datetime.now(IST)
    return now.hour == 10 and now.minute < 15


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    manual = os.getenv("BUILD_CAUSE", "").find("UserId") >= 0 or os.getenv(
        "RUN_TYPE", ""
    ).strip() == "Manual"
    # Jenkins user builds often set BUILD_USER_ID
    if os.getenv("BUILD_USER_ID") or os.getenv("BuildUserCause"):
        manual = True
    if os.getenv("POLL_ONLY", "").strip() in {"1", "true", "TRUE"}:
        manual = False

    try:
        fp = capture_fingerprint()
        save_current(fp)
        changed = compare_with_previous(fp)
    except Exception as exc:
        GATE_PATH.write_text(
            json.dumps({"action": "error", "error": str(exc)}, indent=2),
            encoding="utf-8",
        )
        print(f"GATE_ERROR={exc}")
        return 2

    daily = _is_daily_window()
    force = os.getenv("FORCE_FULL", "").strip() in {"1", "true", "TRUE", "yes"}

    if force or daily:
        action = "run"
        reason = "daily_window" if daily else "force_full"
        run_type = "Daily RUN" if daily else os.getenv("RUN_TYPE", "Manual")
    elif changed:
        action = "run"
        reason = "fingerprint_changed"
        run_type = "Automatic Validation"
    elif manual and os.getenv("SKIP_IF_UNCHANGED", "").strip() not in {
        "1",
        "true",
        "TRUE",
    }:
        # Manual Jenkins/parameterized builds still run unless asked to skip
        action = "run"
        reason = "manual"
        run_type = "Manual"
    else:
        action = "skip"
        reason = "unchanged"
        run_type = "Poll skip"

    gate = {
        "action": action,
        "reason": reason,
        "run_type": run_type,
        "db_changed": changed,
        "daily_window": daily,
        "fingerprint": fp,
        "decided_at_ist": datetime.now(IST).isoformat(timespec="seconds"),
    }
    GATE_PATH.write_text(json.dumps(gate, indent=2), encoding="utf-8")
    print(f"GATE_ACTION={action}")
    print(f"GATE_REASON={reason}")
    print(f"RUN_TYPE={run_type}")
    print(f"DB_CHANGED={changed}")

    return 0 if action == "run" else 3


if __name__ == "__main__":
    raise SystemExit(main())
