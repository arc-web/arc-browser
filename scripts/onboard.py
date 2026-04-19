#!/usr/bin/env python3
"""Verify admin access for a Skool slug. Writes ~/.skool/clients/<id>.json."""
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
from browser import navigate_ready
from skool.scanner import SkoolScanner

SESSION_DIR = Path(SESSIONS_DIR) / "skool"
CLIENTS_DIR = Path.home() / ".skool/clients"


async def verify(slug: str, client_id: str = None):
    if not SESSION_DIR.exists():
        print("No session. Run: python3 scripts/collect.py --setup", file=sys.stderr)
        sys.exit(2)
    CLIENTS_DIR.mkdir(parents=True, exist_ok=True)
    client_id = client_id or slug
    scanner = SkoolScanner(slug)

    _kill_chrome_for_profile(str(SESSION_DIR))
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(SESSION_DIR), headless=True, channel="chrome", viewport={"width": 1440, "height": 900}
        )
        page = await ctx.new_page()
        await navigate_ready(page, scanner.base, post_nav_ms=3000)
        has_settings = await page.evaluate("""
            (() => Array.from(document.querySelectorAll('button')).some(b => b.textContent.trim() === 'Settings'))()
        """)
        await ctx.close()

    record = {
        "client_id": client_id,
        "slug": slug,
        "is_admin": bool(has_settings),
        "verified_at": datetime.now().isoformat(),
    }
    out = CLIENTS_DIR / f"{client_id}.json"
    out.write_text(json.dumps(record, indent=2))
    status = "ADMIN" if has_settings else "NOT ADMIN"
    print(f"{status}: {slug} -> {out}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--slug", required=True)
    p.add_argument("--client-id")
    args = p.parse_args()
    asyncio.run(verify(args.slug, args.client_id))


if __name__ == "__main__":
    main()
