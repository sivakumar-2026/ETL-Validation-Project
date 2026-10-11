"""Build failure-item tables: only-in-target, only-in-source, value mismatch."""

from __future__ import annotations

from typing import Any

from conftest import PRIMARY_KEY

FAIL_ROW_LIMIT = 50


def _cell(value: Any) -> str:
    if value is None:
        return ""
    try:
        import pandas as pd

        if pd.isna(value):
            return ""
    except Exception:
        pass
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def _to_pandas(frame):
    if hasattr(frame, "toPandas"):
        return frame.toPandas()
    return frame


def _empty(columns: list[str]) -> dict:
    return {"columns": columns, "rows": [["—", "—", "—", "(none)"]]}


def failure_item_tables(df_src, df_tgt, primary_key: str = PRIMARY_KEY) -> dict:
    """Return only the three failure-item tables (no sample dumps)."""
    import pandas as pd

    src = _to_pandas(df_src).copy()
    tgt = _to_pandas(df_tgt).copy()
    src.columns = [str(c).upper().replace("_", "") for c in src.columns]
    tgt.columns = [str(c).upper().replace("_", "") for c in tgt.columns]
    pk = primary_key.upper().replace("_", "")

    if pk not in src.columns or pk not in tgt.columns:
        return {
            "Failure items — Value mismatch": {
                "columns": ["note"],
                "rows": [[f"Primary key {pk} not found in both frames"]],
            }
        }

    src = src.drop_duplicates(subset=[pk], keep="first").set_index(pk, drop=False)
    tgt = tgt.drop_duplicates(subset=[pk], keep="first").set_index(pk, drop=False)

    src_keys = set(src.index)
    tgt_keys = set(tgt.index)
    only_tgt = sorted(tgt_keys - src_keys, key=lambda x: (str(type(x)), str(x)))
    only_src = sorted(src_keys - tgt_keys, key=lambda x: (str(type(x)), str(x)))
    common = src_keys & tgt_keys

    compare_cols = [c for c in src.columns if c in tgt.columns and c != pk]

    only_tgt_cols = [pk, "SOURCE", "TARGET TITLE", "TARGET ARTISTID"]
    only_tgt_rows = []
    for key in only_tgt[:FAIL_ROW_LIMIT]:
        row = tgt.loc[key]
        title = _cell(row["TITLE"]) if "TITLE" in tgt.columns else ""
        artist = _cell(row["ARTISTID"]) if "ARTISTID" in tgt.columns else ""
        # generic fallbacks for non-album tables
        if "TITLE" not in tgt.columns:
            title = _cell(row[compare_cols[0]]) if compare_cols else ""
        if "ARTISTID" not in tgt.columns:
            artist = _cell(row[compare_cols[1]]) if len(compare_cols) > 1 else ""
        only_tgt_rows.append([_cell(key), "(not present)", title, artist])

    only_src_cols = [pk, "SOURCE TITLE", "SOURCE ARTISTID", "TARGET"]
    only_src_rows = []
    for key in only_src[:FAIL_ROW_LIMIT]:
        row = src.loc[key]
        title = _cell(row["TITLE"]) if "TITLE" in src.columns else (
            _cell(row[compare_cols[0]]) if compare_cols else ""
        )
        artist = _cell(row["ARTISTID"]) if "ARTISTID" in src.columns else (
            _cell(row[compare_cols[1]]) if len(compare_cols) > 1 else ""
        )
        only_src_rows.append([_cell(key), title, artist, "(not present)"])

    mismatch_cols = [pk, "COLUMN", "SOURCE VALUE", "TARGET VALUE"]
    mismatch_rows = []
    for key in sorted(common, key=lambda x: (str(type(x)), str(x))):
        if len(mismatch_rows) >= FAIL_ROW_LIMIT:
            break
        srow = src.loc[key]
        trow = tgt.loc[key]
        for col in compare_cols:
            sv, tv = srow[col], trow[col]
            same = False
            try:
                same = pd.isna(sv) and pd.isna(tv)
            except Exception:
                pass
            if same:
                continue
            if _cell(sv) != _cell(tv):
                mismatch_rows.append([_cell(key), col, _cell(sv), _cell(tv)])
                if len(mismatch_rows) >= FAIL_ROW_LIMIT:
                    break

    tables = {
        "Failure items — Only in TARGET": {
            "columns": only_tgt_cols,
            "rows": only_tgt_rows or [["—", "—", "—", "(none)"]],
        },
        "Failure items — Only in SOURCE": {
            "columns": only_src_cols,
            "rows": only_src_rows or [["—", "—", "—", "(none)"]],
        },
        "Failure items — Value mismatch": {
            "columns": mismatch_cols,
            "rows": mismatch_rows or [["—", "—", "—", "(none)"]],
        },
    }
    return tables


def extract_samples(item, status: str = "passed") -> dict:
    """On fail with data fixtures: only the three failure-item tables. Else empty."""
    if status != "failed":
        return {}

    funcargs = getattr(item, "funcargs", {}) or {}
    if "get_data" in funcargs:
        src, tgt = funcargs["get_data"]
        return failure_item_tables(src, tgt)
    if "spark_frames" in funcargs:
        src, tgt = funcargs["spark_frames"]
        return failure_item_tables(src, tgt)
    return {}
