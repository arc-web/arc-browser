#!/usr/bin/env python3
"""
CLI runner for Skool audit reports.

Usage:
  python3 scripts/run_scan.py <slug> --from-baseline path.json [--out output.html]

--from-baseline: skip browser scan, load data from JSON and generate report.
                 Use for testing report.py changes against reference data.

Without --from-baseline: live scan requires the MCP server running with an active
                         Skool session. Use Claude Code with /skool-scan instead.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from skool import generate_report, gap_analyze


def main():
    p = argparse.ArgumentParser(description="Generate Skool audit report")
    p.add_argument("slug", help="Skool group slug (e.g. stackpack)")
    p.add_argument("--from-baseline", metavar="FILE", help="JSON file with scan data")
    p.add_argument("--out", metavar="PATH", help="Output HTML path (default: ~/<slug>-audit.html)")
    p.add_argument("--gap-only", action="store_true", help="Print gap analysis to stdout and exit")
    args = p.parse_args()

    if not args.from_baseline:
        print(
            "Live scan via MCP is orchestrated by Claude Code (/skool-scan skill).\n"
            "To test report generation, use: --from-baseline examples/stackpack-baseline.json",
            file=sys.stderr,
        )
        sys.exit(1)

    data = json.loads(Path(args.from_baseline).read_text())
    data.setdefault("slug", args.slug)

    if args.gap_only:
        gap = gap_analyze(data)
        for item in gap:
            status = "OK  " if item["status"] == "Using" else f"MISS"
            print(f"[{status}] [{item['impact'].upper():4}] {item['feature']}")
            if item["action"]:
                print(f"         -> {item['action']}")
        return

    out = generate_report(data, output_path=args.out)
    print(f"Report written: {out}")


if __name__ == "__main__":
    main()
