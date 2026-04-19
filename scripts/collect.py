#!/usr/bin/env python3
"""Autonomous Skool collector. Playwright only - no AI.

Usage:
  python3 scripts/collect.py --setup              # auto-login via 1Password creds, save session
  python3 scripts/collect.py --slug stackpack     # run scan
  python3 scripts/collect.py --slug stackpack --resume
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from patchright.async_api import async_playwright

from browser.context import _kill_chrome_for_profile
from browser.settings import SESSIONS_DIR
from browser import skool_auto_login, skool_verify_auth, navigate_ready
from skool.scanner import SkoolScanner
from skool.paginator import scroll_until_stable

# Single shared Chrome profile - same one the MCP browser-use agent uses
SESSION_DIR = Path(SESSIONS_DIR) / "skool"
SCAN_ROOT = Path.home() / ".skool/scans"

SECTIONS = [
    "about", "members", "categories", "classroom",
    "calendar", "map", "leaderboards", "settings", "posts",
]


async def setup():
    """Auto-login via 1Password credentials. No human interaction required."""
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    _kill_chrome_for_profile(str(SESSION_DIR))

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(SESSION_DIR), headless=False, channel="chrome", viewport={"width": 1440, "height": 900}
        )
        page = await ctx.new_page()
        result = await skool_auto_login(page)
        await ctx.close()
        if result["status"] == "failed":
            print(f"ERROR: {result['reason']}", file=sys.stderr)
            sys.exit(2)
        print(f"{result['status']}: {result['reason']}")
        print(f"Session saved: {SESSION_DIR}")


async def _nav(page, url):
    await navigate_ready(page, url, post_nav_ms=2000)


async def _collect_section(scanner, page, section, raw_dir, resume):
    out = raw_dir / f"{section}.json"
    if resume and out.exists():
        existing = json.loads(out.read_text())
        if "error" not in existing:
            print(f"  [skip] {section} (resume)")
            return existing
        print(f"  [retry] {section} (previous run had error)")
    print(f"  [run ] {section}")
    try:
        data = await _run(scanner, page, section)
    except Exception as e:
        data = {"error": str(e), "section": section}
    out.write_text(json.dumps(data, indent=2, default=str))
    return data


async def _run(scanner, page, section):
    if section == "about":
        await _nav(page, scanner.url_about)
        return await scanner.run_section(page, section, scanner.JS_ABOUT)

    if section == "members":
        await _nav(page, scanner.url_members)
        result = await scroll_until_stable(page, stable_iterations=3, max_iterations=600, wait_ms=600)
        if not result.get("stabilized"):
            print(f"  [warn] members scroll did not stabilize after {result.get('iterations')} iterations - data may be incomplete")
        data = await scanner.run_section(page, section, scanner.JS_MEMBERS_EXTRACT)
        if isinstance(data, dict) and data.get("adminNames"):
            scanner.admin_names = data["adminNames"]
        return data

    if section == "categories":
        await _nav(page, scanner.url_feed)
        return await scanner.run_section(page, section, scanner.JS_CATEGORIES)

    if section == "classroom":
        await _nav(page, scanner.url_classroom)
        listing = await scanner.run_section(page, "classroom_list", scanner.JS_CLASSROOM_LIST)
        courses = []
        count = listing.get("courseCount", 0) if isinstance(listing, dict) else 0
        for i in range(count):
            await _nav(page, scanner.url_classroom)
            await asyncio.sleep(1)
            try:
                await page.evaluate(scanner.js_click_course(i))
                await asyncio.sleep(3)
                detail = await scanner.run_section(page, f"course_{i}", scanner.JS_COURSE_DETAIL)
                courses.append(detail)
            except Exception as e:
                courses.append({"error": str(e), "index": i})
        return {
            "course_count": listing.get("courseCount", 0) if isinstance(listing, dict) else 0,
            "course_names": listing.get("courseNames", []) if isinstance(listing, dict) else [],
            "courses": courses,
        }

    if section == "calendar":
        await _nav(page, scanner.url_calendar)
        return await scanner.run_section(page, section, scanner.JS_CALENDAR)

    if section == "map":
        await _nav(page, scanner.url_map)
        return await scanner.run_section(page, section, scanner.JS_MAP)

    if section == "leaderboards":
        await _nav(page, scanner.url_leaderboards)
        return await scanner.run_section(page, section, scanner.JS_LEADERBOARDS)

    if section == "settings":
        await _nav(page, scanner.url_settings)
        try:
            opened = await page.evaluate(scanner.JS_OPEN_SETTINGS)
            if opened != "opened":
                return {"is_admin": False, "note": "Settings button not visible"}
            await asyncio.sleep(2)
            modal = await scanner.run_section(page, "settings_modal", scanner.JS_MODAL_TEXT)
            return {"is_admin": True, "modal": modal}
        except Exception as e:
            return {"error": str(e)}

    if section == "posts":
        await _nav(page, scanner.url_feed)
        result = await scroll_until_stable(page, stable_iterations=3, max_iterations=200, wait_ms=1000)
        if not result.get("stabilized"):
            print(f"  [warn] posts scroll did not stabilize after {result.get('iterations')} iterations")
        return await scanner.run_section(page, section, scanner.js_extract_posts(scanner.slug))

    return {"error": f"unknown section {section}"}


async def collect(slug: str, resume: bool = False, only: list = None, headless: bool = False):
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    scan_dir = SCAN_ROOT / slug / ts
    if resume:
        existing = sorted((SCAN_ROOT / slug).glob("*")) if (SCAN_ROOT / slug).exists() else []
        if existing:
            scan_dir = existing[-1]
    raw_dir = scan_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    print(f"Scan dir: {scan_dir}")

    if not SESSION_DIR.exists():
        print("No session found. Run `python3 scripts/collect.py --setup` first.", file=sys.stderr)
        sys.exit(2)

    _kill_chrome_for_profile(str(SESSION_DIR))

    scanner = SkoolScanner(slug)
    sections_to_run = only or SECTIONS

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(SESSION_DIR), headless=headless, channel="chrome", viewport={"width": 1440, "height": 900}
        )
        page = await ctx.new_page()

        # Verify auth before running scan
        if not await skool_verify_auth(page):
            print("ERROR: Session is not authenticated. Run `python3 scripts/collect.py --setup` to log in.", file=sys.stderr)
            await ctx.close()
            sys.exit(2)

        merged = {
            "slug": slug,
            "scanned_at": datetime.now().isoformat(),
            "scan_dir": str(scan_dir),
            "community": {},
            "classroom": {},
        }

        for section in sections_to_run:
            data = await _collect_section(scanner, page, section, raw_dir, resume)
            # Map to the nested structure report.py and gap.py expect
            if section == "categories":
                merged["community"]["categories"] = data.get("categories", []) if isinstance(data, dict) else []
            elif section == "classroom":
                merged["classroom"].update(data if isinstance(data, dict) else {})
            else:
                merged[section] = data

        await ctx.close()

    (scan_dir / "raw.json").write_text(json.dumps(merged, indent=2, default=str))
    print(f"\nRaw scan written: {scan_dir / 'raw.json'}")


def main():
    p = argparse.ArgumentParser(description="Autonomous Skool collector")
    p.add_argument("--setup", action="store_true", help="Auto-login via 1Password, save session")
    p.add_argument("--slug", help="Skool group slug")
    p.add_argument("--resume", action="store_true", help="Skip sections already scanned (re-runs errors)")
    p.add_argument("--only", nargs="*", help="Run only these sections")
    p.add_argument("--headless", action="store_true")
    args = p.parse_args()
    if args.setup:
        asyncio.run(setup())
    elif args.slug:
        asyncio.run(collect(args.slug, args.resume, args.only, args.headless))
    else:
        p.print_help()


if __name__ == "__main__":
    main()
