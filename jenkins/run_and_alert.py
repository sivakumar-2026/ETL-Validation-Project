"""Same as run_dashboard.py — kept for Jenkins/scripts that call this path."""

from __future__ import annotations

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    # Delegate to project-root runner (browser + email)
    g = runpy.run_path(str(ROOT / "run_dashboard.py"), run_name="__not_main__")
    return int(g["main"]())


if __name__ == "__main__":
    raise SystemExit(main())
