"""
ARC Browser - MCP Server

Gives Claude Code a stealthy, autonomous browser via natural language tool calls.
Generic by design - site-specific behavior lives in config/site_registry.json.
Includes Skool-specific tools for community auditing.
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
    get_context, current_page,
    navigate_ready, auto_login, verify_auth, with_retry,
)
from router import classify, get_recipe
from agent import run_task
from utils.human import human_click, human_type, human_delay

mcp = FastMCP("arc-browser")

# Persistent rate limiter (survives server restarts)
_RATE_FILE = Path.home() / ".arc-browser" / "rate.json"


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
    c = classify(url, task=task)
    if c["warning"]:
        return f"CONFIRMATION REQUIRED\n{c['warning']}"
    if not _check_rate(c["domain"], c["rate_limit"]):
        return f"Rate limit reached for {c['domain']} ({c['rate_limit']} actions/hr). Try again later."
    try:
        result = await run_task(task, session=session, mode=c["mode"])
        if c["flaresolverr_hint"]:
            return f"ROUTING HINT: {c['flaresolverr_hint']}\n\n{result}"
        return result
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


@mcp.tool()
async def browser_analyze_site(url: str, session: str = "default") -> str:
    """
    Navigate to a URL and analyze page structure: pagination patterns, listing
    selectors, auth walls, CF protection. Returns JSON with agent_hints array.
    Call before planning a scraping or automation workflow against an unfamiliar site.
    """
    from .site_analyzer import analyze_site
    c = classify(url)
    ctx = await get_context(session=session, mode=c["mode"])
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await navigate_ready(page, url)
    result = await analyze_site(page)
    return json.dumps(result, indent=2)


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
        f"CF protected: {c['cf_protected']}",
    ]
    if c["flaresolverr_hint"]:
        lines.append(f"FlareSolverr: {c['flaresolverr_hint']}")
    if c["warning"]:
        lines.append(f"Warning:    {c['warning']}")
    return "\n".join(lines)


@mcp.tool()
async def browser_introspect(url: str) -> str:
    """
    Describe everything arc-browser knows about this URL - mode, auth, waits,
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


# -- Camofox (stealth Firefox sidecar) ----------------------------------------

@mcp.tool()
async def browser_camofox_health() -> str:
    """
    Probe Camofox sidecar (stealth Firefox at port 9377).
    Use when Patchright Chromium is detected by Turnstile/Datadome/PerimeterX.
    Sidecar must be running: `cd ~/ai/tools/browser/camofox-browser && npm start`.
    """
    from camofox import health, check_health
    if not check_health():
        return json.dumps({"ok": False, "error": "sidecar not reachable at http://127.0.0.1:9377"})
    return json.dumps(health(), indent=2)


@mcp.tool()
async def browser_camofox_view(url: str, session: str = "default") -> str:
    """
    Open URL in Camofox (stealth Firefox), return accessibility snapshot, close tab.
    Use for sites that detect Patchright Chromium fingerprint.
    Snapshot is ~90% smaller than HTML and includes element refs (e1, e2) for follow-ups.
    """
    from camofox import open_tab, snapshot, close_tab, check_health
    if not check_health():
        return json.dumps({
            "error": "Camofox sidecar not running",
            "fix": "cd ~/ai/tools/browser/camofox-browser && PORT=9377 node server.js &",
        })
    tab_id = open_tab(url, user_id=session, session_key=session)
    try:
        await asyncio.sleep(3)
        snap = snapshot(tab_id, user_id=session, fmt="text")
        return json.dumps(snap, indent=2)
    finally:
        close_tab(tab_id, user_id=session)


# -- Skool-specific tools -----------------------------------------------------

SKOOL_SESSION = "skool"


@mcp.tool()
async def skool_auth_refresh(force: bool = False) -> str:
    """
    Ensure a valid Skool session exists. Idempotent: skips if already logged in.
    Pulls credentials from 1Password item 'Skool'.
    Returns JSON: {"status": "logged_in"|"already"|"failed", "reason": str}.
    """
    result = await auto_login("skool.com", session=SKOOL_SESSION, force=force)
    return json.dumps(result, indent=2)


@mcp.tool()
async def skool_verify_session() -> str:
    """
    Check whether the Skool session is authenticated without re-logging in.
    Returns JSON: {"authenticated": bool, "url": str}.
    """
    result = await verify_auth("skool.com", session=SKOOL_SESSION)
    return json.dumps(result, indent=2)


@mcp.tool()
async def skool_scan(slug: str, resume: bool = False) -> str:
    """
    Run a full Skool group scan. Writes to ~/.skool/scans/<slug>/<ts>/raw.json.
    Returns the path to the generated raw.json.
    """
    import subprocess as _sp
    scripts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
    cmd = ["python3", os.path.join(scripts_dir, "collect.py"), "--slug", slug]
    if resume:
        cmd.append("--resume")
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return f"scan failed: {stderr.decode()}"
    return stdout.decode()


@mcp.tool()
async def skool_onboard(slug: str, client_id: str = None) -> str:
    """
    Verify admin access for a Skool slug. Writes ~/.skool/clients/<id>.json.
    """
    import subprocess as _sp
    scripts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")
    cmd = ["python3", os.path.join(scripts_dir, "onboard.py"), "--slug", slug]
    if client_id:
        cmd += ["--client-id", client_id]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        return f"onboard failed: {stderr.decode()}"
    return stdout.decode()


if __name__ == "__main__":
    mcp.run()
