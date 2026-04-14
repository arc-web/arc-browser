"""
Ghost Browser - MCP Server

Gives Claude Code a stealthy, autonomous browser via natural language tool calls.
Generic by design - site-specific behavior lives in config/site_registry.json.
"""
import asyncio
import base64
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from mcp.server.fastmcp import FastMCP
from browser import (
    get_context, current_page, close_session,
    navigate_ready, auto_login, verify_auth, with_retry,
)
from router import classify, get_recipe
from agent import run_task
from utils.human import human_click, human_type, human_delay

mcp = FastMCP("ghost-browser")

# Persistent rate limiter (survives server restarts)
_RATE_FILE = Path.home() / ".ghost-browser" / "rate.json"


def _load_rate() -> dict:
    try:
        if _RATE_FILE.exists():
            return json.loads(_RATE_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_rate(state: dict) -> None:
    try:
        _RATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _RATE_FILE.write_text(json.dumps(state))
    except Exception:
        pass


_rate: dict = _load_rate()


def _check_rate(domain: str, limit: int) -> bool:
    b = _rate.get(domain) or {"count": 0, "reset_at": time.time() + 3600}
    if time.time() > b["reset_at"]:
        b = {"count": 0, "reset_at": time.time() + 3600}
    if b["count"] >= limit:
        _rate[domain] = b
        _save_rate(_rate)
        return False
    b["count"] += 1
    _rate[domain] = b
    _save_rate(_rate)
    return True


def _rate_remaining(domain: str, limit: int) -> int:
    b = _rate.get(domain)
    if not b or time.time() > b.get("reset_at", 0):
        return limit
    return max(0, limit - b["count"])


# -- Autonomous task tools ----------------------------------------------------

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
    """
    c = classify(url)
    if not _check_rate(c["domain"], c["rate_limit"]):
        return f"Rate limit reached for {c['domain']}."
    try:
        return await run_task(task, session=session, mode="headed")
    except Exception as e:
        return f"Task failed: {e}"


# -- Primitive tools ----------------------------------------------------------

@mcp.tool()
async def browser_navigate(url: str, session: str = "default",
                           wait_for_selector: str = None) -> str:
    """
    Navigate to a URL. Waits for the page to be actually ready (SPA-safe).
    Optionally waits for a specific CSS selector to appear.
    """
    c = classify(url)
    ctx = await get_context(session=session, mode=c["mode"])
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    recipe = get_recipe(url)
    waits = recipe.get("waits", {}) if recipe else {}
    await navigate_ready(
        page, url,
        wait_for_selector=wait_for_selector,
        wait_until=waits.get("default", "load"),
        post_nav_ms=waits.get("post_nav_ms", 1000),
    )
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
    """Execute JavaScript in the current page and return the result. Retries transient failures."""
    page = current_page(session)
    result = await with_retry(lambda: page.evaluate(js), attempts=3)
    return str(result)


@mcp.tool()
async def browser_wait(selector: str, timeout: int = 10000, session: str = "default") -> str:
    """Wait for an element to appear on the page."""
    page = current_page(session)
    await page.wait_for_selector(selector, timeout=timeout)
    return f"Element found: {selector}"


# -- Classification + introspection -------------------------------------------

@mcp.tool()
async def browser_preflight(url: str) -> str:
    """Preview what mode will be used for a URL before running a task."""
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
async def browser_introspect(url: str) -> str:
    """
    Describe everything ghost-browser knows about this URL - mode, auth, waits,
    rate limit remaining, recipe notes. Call this before acting on an unfamiliar
    site to figure out which primitives are available and what to expect.

    Returns JSON with fields: domain, mode, auth_required, available_recipes,
    rate_limit_remaining, known_waits, notes.
    """
    c = classify(url)
    recipe = get_recipe(url)
    auth = recipe.get("auth") if recipe else None
    available = ["navigate_ready"]
    if auth:
        available += ["auto_login", "verify_auth"]
    report = {
        "domain": c["domain"],
        "mode": c["mode"],
        "risk": c["risk"],
        "disruptive": c["disruptive"],
        "auth_required": bool(auth),
        "auth_verify_url": (auth or {}).get("verify_url"),
        "available_recipes": available,
        "rate_limit": c["rate_limit"],
        "rate_limit_remaining": _rate_remaining(c["domain"], c["rate_limit"]),
        "known_waits": recipe.get("waits", {}) if recipe else {},
        "notes": recipe.get("notes") if recipe else "No recipe - using defaults. Add one to config/site_registry.json for better behavior.",
        "warning": c["warning"],
    }
    return json.dumps(report, indent=2)


@mcp.tool()
async def browser_plan_action(url: str, goal: str) -> str:
    """
    Return a suggested primitive-call sequence to accomplish `goal` on `url`.

    Structured fast path: if the goal matches a recipe-backed capability (e.g. "log in"),
    returns the exact sequence. Otherwise returns a stub asking the conversing agent
    (you, Claude Code) to plan the steps using the introspection result.
    """
    c = classify(url)
    recipe = get_recipe(url)
    g = goal.lower().strip()

    structured = None
    if any(kw in g for kw in ("log in", "login", "sign in", "authenticate")):
        if recipe.get("auth"):
            structured = [
                {"tool": "browser_auto_login", "args": {"site_id": c["domain"]}},
                {"tool": "browser_verify_auth", "args": {"site_id": c["domain"]}},
            ]
    elif "verify" in g and "auth" in g:
        if recipe.get("auth"):
            structured = [{"tool": "browser_verify_auth", "args": {"site_id": c["domain"]}}]
    elif "navigate" in g or "go to" in g or "open" in g:
        structured = [{"tool": "browser_navigate", "args": {"url": url}}]

    if structured:
        return json.dumps({"plan": structured, "source": "recipe"}, indent=2)

    return json.dumps({
        "plan": None,
        "source": "unplanned",
        "instruction": (
            "No structured recipe for this goal. Call browser_introspect(url) to see what "
            "primitives are available, then compose a sequence of navigate/click/type/evaluate "
            "calls yourself based on the page's accessibility snapshot (browser_snapshot)."
        ),
        "introspection": json.loads(await browser_introspect(url)),
    }, indent=2)


# -- Auth tools ---------------------------------------------------------------

@mcp.tool()
async def browser_auto_login(site_id: str, force: bool = False) -> str:
    """
    Auto-login for a known site. Looks up the auth recipe in site_registry.json,
    pulls credentials from 1Password, fills the login form, and verifies redirect.

    Idempotent: returns "already" if a valid session already exists (unless force=True).

    Returns JSON: {"status": "logged_in"|"already"|"failed", "reason": str}.
    """
    result = await auto_login(site_id, force=force)
    return json.dumps(result, indent=2)


@mcp.tool()
async def browser_verify_auth(site_id: str) -> str:
    """
    Check whether the stored session for `site_id` is still authenticated.
    Navigates to the recipe's verify_url and checks for login redirect.

    Returns JSON: {"authenticated": bool, "reason": str}.
    """
    result = await verify_auth(site_id)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()
