"""Send validation alert email via Gmail SMTP with PDF attachment."""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv(ROOT / ".env")

from run_meta import write_meta  # noqa: E402

REPORT_DIR = ROOT / "reports"
BODY_PATH = REPORT_DIR / "email_body.txt"
SUBJECT_PATH = REPORT_DIR / "email_subject.txt"
SUMMARY_PATH = REPORT_DIR / "validation_summary.json"
PDF_PATH = REPORT_DIR / "validation_report.pdf"


def main() -> int:
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    to_addr = os.getenv("ALERT_EMAIL", "sivakumartorur@gmail.com").strip()
    from_addr = os.getenv("SMTP_FROM", user).strip()

    if not user or not password:
        print(
            "SMTP not configured.\n"
            "Add SMTP_USER / SMTP_PASSWORD / ALERT_EMAIL to .env"
        )
        return 2

    if not BODY_PATH.exists():
        print(f"Missing {BODY_PATH}. Run: python3 jenkins/build_email.py")
        return 1

    body = BODY_PATH.read_text(encoding="utf-8")
    meta = write_meta()
    subject = (
        SUBJECT_PATH.read_text(encoding="utf-8").strip()
        if SUBJECT_PATH.exists()
        else meta["subject"]
    )

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    attached = None
    if PDF_PATH.exists():
        part = MIMEApplication(PDF_PATH.read_bytes(), Name=PDF_PATH.name)
        part["Content-Disposition"] = f'attachment; filename="{PDF_PATH.name}"'
        msg.attach(part)
        attached = PDF_PATH.name
    else:
        html_fallback = REPORT_DIR / "validation_dashboard.html"
        if html_fallback.exists():
            part = MIMEApplication(html_fallback.read_bytes(), Name=html_fallback.name)
            part["Content-Disposition"] = f'attachment; filename="{html_fallback.name}"'
            msg.attach(part)
            attached = html_fallback.name
            print(f"WARNING: PDF missing — attaching {attached} instead")
        else:
            print("WARNING: No PDF/HTML attachment — sending body only")

    context = ssl.create_default_context()
    try:
        import certifi

        context.load_verify_locations(certifi.where())
    except Exception:
        pass

    with smtplib.SMTP(host, port, timeout=60) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(user, password)
        server.sendmail(from_addr, [to_addr], msg.as_string())

    print(f"Email sent to {to_addr}")
    print(f"Subject: {subject}")
    print(f"Attached: {attached or '(none)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
