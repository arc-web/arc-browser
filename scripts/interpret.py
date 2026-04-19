#!/usr/bin/env python3
"""Claude Code handoff interpreter.

No API call. This script reads raw.json + runs gap analysis, then writes a
prompt file you open in Claude Code. Claude fills in narratives.json next to
it; re-running this script merges narratives into interpreted.json.

Usage:
  python3 scripts/interpret.py --scan ~/.skool/scans/<slug>/<ts>/raw.json
      -> writes prompt.md + data.json in that dir, tells you what to do

  (after Claude writes narratives.json in the same dir)
  python3 scripts/interpret.py --scan ~/.skool/scans/<slug>/<ts>/raw.json --merge
      -> writes interpreted.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from skool import gap_analyze


PROMPT_TEMPLATE = """# Skool Audit Interpretation - {slug}

You have the scan data at `data.json` in this directory and the gap analysis
included below. Produce `narratives.json` in this same directory matching the
schema at the bottom. Then run:

    python3 scripts/interpret.py --scan {raw_path} --merge

## Gap analysis results

{gap_summary}

## Your task

Write `narratives.json` with:

```json
{{
  "executive_summary": "3-4 sentence overview of the group's health and biggest opportunities",
  "narratives": {{
    "<feature_name>": "1-2 sentence assessment specific to this group's data"
  }},
  "actions": {{
    "high": [{{"title": "...", "reasoning": "2-sentence why"}}],
    "med":  [{{"title": "...", "reasoning": "..."}}],
    "low":  [{{"title": "...", "reasoning": "..."}}]
  }}
}}
```

Feature names to cover in narratives: {features}
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scan", required=True)
    p.add_argument("--merge", action="store_true", help="Merge narratives.json into interpreted.json")
    args = p.parse_args()

    raw_path = Path(args.scan).expanduser()
    if not raw_path.exists():
        print(f"Not found: {raw_path}", file=sys.stderr)
        sys.exit(2)

    raw = json.loads(raw_path.read_text())
    gap = gap_analyze(raw)
    scan_dir = raw_path.parent

    if args.merge:
        narratives_path = scan_dir / "narratives.json"
        if not narratives_path.exists():
            print(f"Missing: {narratives_path}\nClaude should write this file first.", file=sys.stderr)
            sys.exit(2)
        narratives = json.loads(narratives_path.read_text())
        merged = {**raw, "gap": gap, "interpretation": narratives}
        out = scan_dir / "interpreted.json"
        out.write_text(json.dumps(merged, indent=2, default=str))
        print(f"Merged: {out}")
        return

    (scan_dir / "data.json").write_text(json.dumps({"scan": raw, "gap": gap}, indent=2, default=str))

    features = sorted({g["feature"] for g in gap})
    gap_lines = []
    for g in gap:
        mark = "OK  " if g["status"] == "Using" else "MISS"
        gap_lines.append(f"  [{mark}] [{g['impact'].upper():4}] {g['feature']}")
        if g.get("action"):
            gap_lines.append(f"         -> {g['action']}")

    prompt = PROMPT_TEMPLATE.format(
        slug=raw.get("slug", "unknown"),
        raw_path=raw_path,
        gap_summary="\n".join(gap_lines),
        features=", ".join(features),
    )
    (scan_dir / "prompt.md").write_text(prompt)

    print(f"Prompt written: {scan_dir / 'prompt.md'}")
    print(f"Data written:   {scan_dir / 'data.json'}")
    print("")
    print("Next: open the prompt in Claude Code, produce narratives.json in that dir, then:")
    print(f"  python3 scripts/interpret.py --scan {raw_path} --merge")


if __name__ == "__main__":
    main()
