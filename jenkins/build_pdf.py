"""Build color-rich PDF = browser HTML dashboard (same look).

Uses Playwright Chromium so gradients/colors/charts match the HTML report.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / "reports"
HTML_PATH = REPORT_DIR / "validation_dashboard.html"
PDF_PATH = REPORT_DIR / "validation_report.pdf"


def main() -> int:
    if not HTML_PATH.exists():
        print(f"Missing dashboard HTML: {HTML_PATH}")
        print("Run jenkins/ci_validate.py first.")
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is required for color PDF matching the HTML report.")
        print("Run: python3 -m pip install playwright && python3 -m playwright install chromium")
        return 1

    uri = HTML_PATH.resolve().as_uri() + "?print=1"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(uri, wait_until="networkidle")
        # let donut chart + cards paint
        page.wait_for_timeout(500)
        page.pdf(
            path=str(PDF_PATH),
            format="A4",
            print_background=True,
            margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"},
        )
        browser.close()

    print(f"PDF={PDF_PATH}")
    print("PDF matches browser HTML dashboard (color + layout).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
