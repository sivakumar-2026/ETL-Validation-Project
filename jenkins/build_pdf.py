"""Build a clean PDF report from validation_summary.json (not raw HTML dump)."""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_meta import write_meta  # noqa: E402

REPORT_DIR = ROOT / "reports"
SUMMARY = REPORT_DIR / "validation_summary.json"
PDF_PATH = REPORT_DIR / "validation_report.pdf"
PDF_HTML = REPORT_DIR / "validation_report_print.html"


def _esc(v) -> str:
    return html.escape("" if v is None else str(v))


def _table_html(title: str, table: dict) -> str:
    cols = table.get("columns") or []
    rows = table.get("rows") or []
    head = "".join(f"<th>{_esc(c)}</th>" for c in cols)
    body = ""
    for row in rows[:50]:
        body += "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>"
    return f"""
    <h3>{_esc(title)}</h3>
    <table>
      <thead><tr>{head}</tr></thead>
      <tbody>{body}</tbody>
    </table>
    """


def _pick_failure_tables(failed_tests: list[dict]) -> dict:
    for t in failed_tests:
        samples = t.get("samples") or {}
        if any(k.startswith("Failure items") for k in samples):
            return samples
    return {}


def build_print_html(data: dict, run_type: str) -> str:
    t = data.get("totals", {})
    failed = [x for x in data.get("tests", []) if x.get("status") == "failed"]
    passed = int(t.get("passed", 0))
    fail_n = int(t.get("failed", 0))
    fp = data.get("db_fingerprint", {})
    status = "FAILED" if fail_n else "PASSED"
    status_color = "#c0392b" if fail_n else "#1e8449"

    fail_list = "".join(
        f"<li>{_esc(f.get('suite'))}.{_esc(f.get('name'))}</li>" for f in failed
    ) or "<li>None</li>"

    tables = _pick_failure_tables(failed)
    tables_html = ""
    for title in (
        "Failure items — Only in TARGET",
        "Failure items — Only in SOURCE",
        "Failure items — Value mismatch",
    ):
        if title in tables:
            tables_html += _table_html(title, tables[title])

    src = fp.get("source", {})
    tgt = fp.get("target", {})

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  body {{ font-family: Helvetica, Arial, sans-serif; color: #1a1a1a; font-size: 12px; }}
  h1 {{ font-size: 20px; margin-bottom: 4px; }}
  h2 {{ font-size: 14px; margin-top: 22px; color: #333; }}
  h3 {{ font-size: 12px; margin-top: 16px; color: #444; }}
  .meta {{ color: #555; margin-bottom: 16px; }}
  .kpis {{ width: 100%; border-collapse: collapse; margin: 12px 0 18px; }}
  .kpis td {{ border: 1px solid #ddd; padding: 10px; text-align: center; width: 25%; }}
  .kpis .label {{ color: #666; font-size: 10px; text-transform: uppercase; }}
  .kpis .value {{ font-size: 22px; font-weight: bold; margin-top: 4px; }}
  .status {{ display: inline-block; padding: 4px 10px; border-radius: 4px;
             color: white; background: {status_color}; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; font-size: 10px; }}
  th {{ background: #f0f3f7; }}
  ul {{ margin: 6px 0 0 18px; padding: 0; }}
</style>
</head>
<body>
  <h1>ETL QA Validation Report</h1>
  <div class="meta">
    <span class="status">{_esc(status)}</span>
    &nbsp; Run type: <strong>{_esc(run_type)}</strong><br/>
    Generated: {_esc(data.get('generated_at', ''))}
  </div>

  <table class="kpis">
    <tr>
      <td><div class="label">Total</div><div class="value">{_esc(t.get('total', 0))}</div></td>
      <td><div class="label">Pass</div><div class="value" style="color:#1e8449">{_esc(passed)}</div></td>
      <td><div class="label">Fail</div><div class="value" style="color:#c0392b">{_esc(fail_n)}</div></td>
      <td><div class="label">Skip</div><div class="value">{_esc(t.get('skipped', 0))}</div></td>
    </tr>
  </table>

  <h2>Data fingerprint</h2>
  <table>
    <tr><th>System</th><th>Table</th><th>Rows</th><th>Max PK</th></tr>
    <tr><td>Source</td><td>{_esc(src.get('table'))}</td><td>{_esc(src.get('count'))}</td><td>{_esc(src.get('max_pk'))}</td></tr>
    <tr><td>Target</td><td>{_esc(tgt.get('table'))}</td><td>{_esc(tgt.get('count'))}</td><td>{_esc(tgt.get('max_pk'))}</td></tr>
  </table>

  <h2>Failed tests</h2>
  <ul>{fail_list}</ul>

  <h2>Failure details</h2>
  {tables_html if tables_html else "<p>No failure-item tables (all checks passed).</p>"}
</body>
</html>
"""


def html_to_pdf(html_text: str, pdf_path: Path) -> None:
    try:
        from xhtml2pdf import pisa
    except ImportError as exc:
        raise SystemExit(
            "xhtml2pdf is required. Run: python3 -m pip install xhtml2pdf"
        ) from exc

    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with pdf_path.open("wb") as out:
        result = pisa.CreatePDF(html_text, dest=out, encoding="utf-8")
    if result.err:
        raise SystemExit(f"PDF generation failed with {result.err} error(s)")


def main() -> int:
    if not SUMMARY.exists():
        print("No validation summary found. Run jenkins/ci_validate.py first.")
        return 1

    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    meta = write_meta()
    html_text = build_print_html(data, meta["run_type"])
    PDF_HTML.write_text(html_text, encoding="utf-8")
    html_to_pdf(html_text, PDF_PATH)
    print(f"PDF={PDF_PATH}")
    print(f"PRINT_HTML={PDF_HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
