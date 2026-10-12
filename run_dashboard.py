"""Manual run from Cursor (Run button) or terminal.

1) Runs ETL validation
2) Opens interactive HTML dashboard in the browser
3) Builds PDF + sends email alert

Usage:
  python3 run_dashboard.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable
HTML_PATH = ROOT / "reports" / "validation_dashboard.html"
PDF_PATH = ROOT / "reports" / "validation_report.pdf"


def _run(script: str, env: dict) -> int:
    print(f"\n>>> Running jenkins/{script}  (python={PY})")
    code = subprocess.call([PY, str(ROOT / "jenkins" / script)], cwd=str(ROOT), env=env)
    print(f"<<< jenkins/{script} exit={code}")
    return code


def main() -> int:
    env = os.environ.copy()
    # Cursor / terminal run is always Manual, even if the DB fingerprint changed.
    env["RUN_TYPE"] = "Manual"

    code = _run("ci_validate.py", env)

    if HTML_PATH.exists():
        webbrowser.open(HTML_PATH.resolve().as_uri())
        print(f"Browser opened: {HTML_PATH}")
    else:
        print("WARNING: HTML dashboard not found")

    _run("build_email.py", env)

    pdf_code = _run("build_pdf.py", env)
    if pdf_code != 0 or not PDF_PATH.exists():
        print(
            "WARNING: PDF build failed. "
            "Install with: python3 -m pip install xhtml2pdf\n"
            "Will still try to send email (may fail if PDF required)."
        )

    send_code = _run("send_email.py", env)
    if send_code != 0:
        print(
            "\nEMAIL FAILED.\n"
            "Quick retry:\n"
            "  python3 jenkins/build_pdf.py\n"
            "  python3 jenkins/send_email.py\n"
            "Check SMTP_* in .env and Spam folder."
        )
        return send_code

    print("\nDone: browser dashboard + email (PDF) sent")
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
