"""
ARC Browser - MCP Server
Stealth browser automation for Claude Code via MCP.
"""
import asyncio
import base64
import os
import sys
import time
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP
from browser import get_context, current_page, close_session
from router import classify
from agent import run_task
from utils.human import human_click, human_type, human_delay

mcp = FastMCP("ghost-browser")

# Simple in-memory rate limiter
_rate: dict = defaultdict(lambda: {"count": 0, "reset_at": time.time() + 3600})

def _check_rate(domain: str, limit: int) -> bool:
    b = _rate[domain]
    if time.time() > b["reset_at"]:
        b["count"] = 0
        b["reset_at"] = time.time() + 3600
    if b["count"] >= limit:
        return False
    b["count"] += 1
    return True


# -- Core tools ---------------------------------------------------------------

@mcp.tool()
async def browser_task(task: str, url: str, session: str = "default") -> str:
    """
    Run a natural language browser task autonomously.
    Router picks the right browser mode. Returns result when done.
    For LinkedIn/Twitter/Facebook, returns a warning - use browser_task_confirmed() instead.
    """
    c = classify(url)

    if c["warning"]:
        return f"CONFIRMATION REQUIRED\n{c['warning']}"

    if not _check_rate(c["domain"], c["rate_limit"]):
        return f"Rate limit reached for {c['domain']} ({c['rate_limit']} actions/hr). Try again later."

    try:
        return await run_task(task, session=session, mode=c["mode"])
    except Exception as e:
        return f"Task failed: {e}"


@mcp.tool()
async def browser_task_confirmed(task: str, url: str, session: str = "default") -> str:
    """
    Run a task that requires CDP (LinkedIn, Twitter, etc).
    User must explicitly call this to confirm the disruption is acceptable.
    Requires Chrome running with: --remote-debugging-port=9222
    """
    c = classify(url)
    if not _check_rate(c["domain"], c["rate_limit"]):
        return f"Rate limit reached for {c['domain']}."
    try:
        return await run_task(task, session=session, mode="headed")
    except Exception as e:
        return f"Task failed: {e}"


@mcp.tool()
async def browser_navigate(url: str, session: str = "default") -> str:
    """Navigate to a URL. Uses the appropriate browser mode for the site."""
    c = classify(url)
    ctx = await get_context(session=session, mode=c["mode"])
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await page.goto(url, wait_until="domcontentloaded")
    await human_delay(1.0, 2.5)
    return f"Navigated to {url}"


@mcp.tool()
async def browser_snapshot(session: str = "default") -> str:
    """Return the accessibility tree of the current page (structured, low token cost)."""
    page = current_page(session)
    snap = await page.accessibility.snapshot()
    return str(snap)


@mcp.tool()
async def browser_screenshot(session: str = "default") -> str:
    """Take a screenshot of the current page. Returns base64 PNG."""
    page = current_page(session)
    data = await page.screenshot(full_page=False)
    return base64.b64encode(data).decode()


@mcp.tool()
async def browser_click(selector: str, session: str = "default") -> str:
    """Click an element using a CSS selector, with human-like mouse movement."""
    page = current_page(session)
    await human_click(page, selector)
    await human_delay(0.5, 1.5)
    return f"Clicked: {selector}"


@mcp.tool()
async def browser_type(selector: str, text: str, session: str = "default") -> str:
    """Type text into a field with human-like per-character timing."""
    page = current_page(session)
    await human_type(page, selector, text)
    return f"Typed {len(text)} chars into {selector}"


@mcp.tool()
async def browser_evaluate(js: str, session: str = "default") -> str:
    """Execute JavaScript in the current page and return the result."""
    page = current_page(session)
    result = await page.evaluate(js)
    return str(result)


@mcp.tool()
async def browser_wait(selector: str, timeout: int = 10000, session: str = "default") -> str:
    """Wait for an element to appear on the page."""
    page = current_page(session)
    await page.wait_for_selector(selector, timeout=timeout)
    return f"Element found: {selector}"


@mcp.tool()
async def browser_preflight(url: str) -> str:
    """
    Preview what mode will be used for a URL before running a task.
    Optional - browser_task() handles this automatically.
    """
    c = classify(url)
    lines = [
        f"Domain:     {c['domain']}",
        f"Risk:       {c['risk']}",
        f"Mode:       {c['mode']}",
        f"Disruptive: {c['disruptive']}",
        f"Rate limit: {c['rate_limit']} actions/hr",
    ]
    if c["warning"]:
        lines.append(f"Warning:    {c['warning']}")
    return "\n".join(lines)


@mcp.tool()
async def browser_skool_setup() -> str:
    """
    One-time Skool session setup. Opens browser to Skool login page.
    Log in manually (handle the CAPTCHA), then call browser_skool_setup_done().
    Credentials are pulled from 1Password automatically after login.
    """
    ctx = await get_context(session="skool", mode="headed")
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await page.goto("https://www.skool.com/login")
    return (
        "Browser opened to Skool login. "
        "Log in manually (complete any CAPTCHA). "
        "Session will be saved automatically when you close the browser or call browser_skool_setup_done()."
    )


@mcp.tool()
async def browser_skool_setup_done() -> str:
    """
    Call this after manually logging in to Skool to save the session.
    Future tasks on skool.com will reuse this session - no CAPTCHA needed.
    """
    await close_session("skool")
    return "Skool session saved to sessions/skool/. Future tasks will skip login."


if __name__ == "__main__":
    mcp.run()
