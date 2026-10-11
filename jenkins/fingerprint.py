"""Shared DB fingerprint helpers for poll gate + CI validation."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))
from dashboard.timeutil import now_ist_iso, now_ist_label  # noqa: E402
REPORT_DIR = ROOT / "reports"
FP_PATH = REPORT_DIR / "db_fingerprint.json"
PREV_FP_PATH = REPORT_DIR / "db_fingerprint.prev.json"
GATE_PATH = REPORT_DIR / "poll_gate.json"


def stats(engine, table: str, pk: str) -> dict:
    from sqlalchemy import text

    with engine.connect() as conn:
        cnt = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        mx = conn.execute(text(f"SELECT MAX({pk}) FROM {table}")).scalar()
        return {"count": int(cnt), "max_pk": str(mx)}


def capture_fingerprint() -> dict:
    from conftest import SRC_ENGINE, SRC_TABLE, TGT_ENGINE, TGT_TABLE

    src_pk = "AlbumId" if "album" in SRC_TABLE.lower() else "AlbumId"
    tgt_pk = "album_id" if "album" in TGT_TABLE.lower() else "album_id"
    return {
        "captured_at": now_ist_label(),
        "captured_at_iso": now_ist_iso(),
        "source": {"table": SRC_TABLE, **stats(SRC_ENGINE, SRC_TABLE, src_pk)},
        "target": {"table": TGT_TABLE, **stats(TGT_ENGINE, TGT_TABLE, tgt_pk)},
    }


def compare_with_previous(fp: dict) -> bool:
    """True if source/target fingerprint differs from last successful validation."""
    if not PREV_FP_PATH.exists():
        return True  # first run — treat as changed so we establish a baseline
    prev = json.loads(PREV_FP_PATH.read_text(encoding="utf-8"))
    return prev.get("source") != fp.get("source") or prev.get("target") != fp.get("target")


def save_current(fp: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    FP_PATH.write_text(json.dumps(fp, indent=2), encoding="utf-8")


def promote_previous(fp: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    PREV_FP_PATH.write_text(json.dumps(fp, indent=2), encoding="utf-8")
