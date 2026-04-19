#!/usr/bin/env python3
"""Render interpreted scan to HTML at ~/Reports/<slug>-<date>-audit.html."""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from skool import generate_report

REPORTS_DIR = Path.home() / "Reports"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scan", required=True, help="Path to interpreted.json (or raw.json)")
    p.add_argument("--out", help="Override output path")
    args = p.parse_args()

    path = Path(args.scan).expanduser()
    data = json.loads(path.read_text())
    slug = data.get("slug", "unknown")

    REPORTS_DIR.mkdir(exist_ok=True)
    out = Path(args.out).expanduser() if args.out else REPORTS_DIR / f"{slug}-{date.today().isoformat()}-audit.html"
    generate_report(data, output_path=str(out))
    print(f"HTML: {out}")


if __name__ == "__main__":
    main()
