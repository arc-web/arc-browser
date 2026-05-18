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

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "arc_browser"

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from mcp.server.fastmcp import FastMCP
from .browser import (
    get_context, current_page,
    navigate_ready, auto_login, verify_auth, with_retry,
    wait_for_hydration, extract_modal_text, tick_all_checkboxes, click_by_text,
)
from .utils.prompt import agentic_browser_prompt
from .router import classify, get_recipe
from .agent import run_task
from .utils.human import human_click, human_type, human_delay
from .google_cloud import (
    build_prepare_packet,
    classify_blocker as classify_google_cloud_blocker,
    read_state as read_google_cloud_state,
    save_state as save_google_cloud_state,
)

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
    """Return a structured snapshot of the current page.

    Patchright dropped the `page.accessibility` namespace. This implementation
    walks the live DOM in-page and emits a compact a11y-style tree with role,
    name, level, and short text snippets - sufficient for LLM-driven planning
    at a fraction of full HTML tokens.
    """
    page = current_page(session)
    js = """
(() => {
  const ROLE_MAP = {
    A:'link', BUTTON:'button', INPUT:'textbox', TEXTAREA:'textbox',
    SELECT:'combobox', NAV:'navigation', MAIN:'main', HEADER:'banner',
    FOOTER:'contentinfo', ASIDE:'complementary', FORM:'form', LABEL:'label',
    UL:'list', OL:'list', LI:'listitem', H1:'heading', H2:'heading',
    H3:'heading', H4:'heading', H5:'heading', H6:'heading',
    IMG:'img', SECTION:'region', ARTICLE:'article', TABLE:'table',
    TR:'row', TD:'cell', TH:'columnheader', DIALOG:'dialog',
  };
  function nameOf(el){
    return (el.getAttribute('aria-label') || el.getAttribute('alt') ||
            el.getAttribute('title') || el.getAttribute('placeholder') ||
            (el.tagName==='INPUT' ? (el.value||el.type||'') : '') ||
            (el.innerText||'').trim().split('\\n')[0].slice(0,120) || '');
  }
  function walk(el, depth){
    if (!el || depth>10) return null;
    if (el.nodeType !== 1) return null;
    if (el.offsetParent===null && el.tagName!=='BODY' && el.tagName!=='DIALOG') return null;
    const role = el.getAttribute('role') || ROLE_MAP[el.tagName];
    const name = nameOf(el);
    const node = (role || name) ? {role: role||'generic', name: name.slice(0,140), tag: el.tagName.toLowerCase()} : null;
    const children = [];
    for (const c of el.children){
      const sub = walk(c, depth+1);
      if (sub) children.push(sub);
    }
    if (node){ if (children.length) node.children = children; return node; }
    if (children.length===1) return children[0];
    if (children.length>1) return {role:'generic', children};
    return null;
  }
  const tree = walk(document.body, 0) || {role:'generic'};
  return JSON.stringify({url: location.href, title: document.title, tree}, null, 2);
})()
"""
    result = await page.evaluate(js)
    return result


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
    from .camofox import health, check_health
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
    from .camofox import open_tab, snapshot, close_tab, check_health
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


# -- Google Cloud OAuth setup recipes ----------------------------------------

@mcp.tool()
async def browser_google_cloud_prepare_oauth(
    account: str,
    services: str,
    project_policy: str = "prompt",
    project_id: str = "",
    session: str = "default",
) -> str:
    """
    Prepare Google Cloud Console for OAuth setup.

    Uses stable Google Cloud URLs first and returns a handoff packet when login,
    CAPTCHA, billing, terms, consent, or final client-secret download requires a
    human decision.
    """
    if project_policy not in ("prompt", "existing"):
        return json.dumps({
            "status": "failed",
            "reason": "invalid_project_policy",
            "valid_project_policy": ["prompt", "existing"],
        }, indent=2)

    packet = build_prepare_packet(account, services, project_policy, project_id, session)
    try:
        ctx = await get_context(session=session, mode="headed")
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await navigate_ready(page, packet["start_url"], post_nav_ms=1500)
        try:
            text = await page.locator("body").inner_text(timeout=3000)
        except Exception:
            text = await page.evaluate("document.body ? document.body.innerText : document.title")
        text = text[:6000] if text else ""
        blocker = classify_google_cloud_blocker(page.url, text)
        packet.update({
            "status": "handoff_required" if blocker else "ready",
            "handoff_reason": blocker,
            "current_url": page.url,
            "diagnostics": {
                "snapshot_excerpt": text[:2000],
            },
            "next_action": (
                "Resolve the handoff reason in the visible browser, then call browser_google_cloud_resume."
                if blocker else
                "Use the stable_urls and selectors to enable APIs, configure consent, and create a Desktop OAuth client."
            ),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
    except Exception as exc:
        packet.update({
            "status": "failed",
            "handoff_reason": "browser_error",
            "error": str(exc),
            "next_action": "Inspect the visible browser session or call browser_google_cloud_status for the saved packet.",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

    state_file = save_google_cloud_state(session, packet)
    packet["state_file"] = str(state_file)
    return json.dumps(packet, indent=2)


@mcp.tool()
async def browser_google_cloud_status(session: str) -> str:
    """Return the saved Google Cloud OAuth setup packet for a browser session."""
    state = read_google_cloud_state(session)
    if not state:
        return json.dumps({
            "status": "not_found",
            "session": session,
            "next_action": "Call browser_google_cloud_prepare_oauth first.",
        }, indent=2)
    return json.dumps(state, indent=2)


@mcp.tool()
async def browser_google_cloud_resume(session: str) -> str:
    """Resume Google Cloud OAuth setup from the saved session packet."""
    state = read_google_cloud_state(session)
    if not state:
        return json.dumps({
            "status": "not_found",
            "session": session,
            "next_action": "Call browser_google_cloud_prepare_oauth first.",
        }, indent=2)
    return await browser_google_cloud_prepare_oauth(
        account=state.get("account", ""),
        services=",".join(state.get("services", [])),
        project_policy=state.get("project_policy", "prompt"),
        project_id=state.get("project_id", ""),
        session=session,
    )


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


# ---------------------------------------------------------------------------
# GHL (GoHighLevel) dedicated tool surface
# ---------------------------------------------------------------------------

GHL_SESSION = "ghl"
GHL_DOMAIN = "app.gohighlevel.com"


@mcp.tool()
async def ghl_auth_refresh(force: bool = False) -> str:
    """Ensure a valid GoHighLevel session exists.

    Uses the google_sso flow in site_registry. Pauses for 2FA via
    #agentic-browser if Google challenges. Idempotent.
    Returns JSON: {status, reason}.
    """
    result = await auto_login(GHL_DOMAIN, session=GHL_SESSION, force=force)
    return json.dumps(result, indent=2)


@mcp.tool()
async def ghl_verify_session() -> str:
    """Check whether the GHL session is authenticated without re-logging in.
    Returns JSON: {authenticated, reason}.
    """
    result = await verify_auth(GHL_DOMAIN, session=GHL_SESSION)
    return json.dumps(result, indent=2)


@mcp.tool()
async def ghl_switch_view(view: str = "agency") -> str:
    """Switch GHL UI between 'agency' and 'subaccount' context.

    Args:
      view: 'agency' or 'subaccount' (with location_id) - currently only 'agency' supported.
    Returns JSON: {ok, url}.
    """
    ctx = await get_context(session=GHL_SESSION, mode="headed")
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    if view == "agency":
        await page.goto("https://app.gohighlevel.com/agency_dashboard?tab=summary",
                        wait_until="load", timeout=30000)
        await wait_for_hydration(page, max_ms=8000)
    else:
        return json.dumps({"ok": False, "reason": "use ghl_switch_subaccount(location_id) for sub-account view"})
    return json.dumps({"ok": True, "url": page.url})


@mcp.tool()
async def ghl_switch_subaccount(location_id: str) -> str:
    """Switch GHL UI into a specific sub-account by location_id.

    Returns JSON: {ok, url}.
    """
    ctx = await get_context(session=GHL_SESSION, mode="headed")
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    await page.goto(f"https://app.gohighlevel.com/v2/location/{location_id}/",
                    wait_until="load", timeout=30000)
    await wait_for_hydration(page, max_ms=10000)
    return json.dumps({"ok": location_id in page.url, "url": page.url})


@mcp.tool()
async def ghl_create_pit(level: str = "agency", name: str = "stackpack-full",
                          scopes: str = "all") -> str:
    """Create a Private Integration Token in GoHighLevel.

    Args:
      level: 'agency' or 'subaccount' (run ghl_switch_subaccount first for subaccount)
      name: integration name
      scopes: 'all' (tick everything) or comma-separated list

    Drives the 5-step UI flow:
      Settings -> Private Integrations -> Create New -> tick scopes -> Submit
      -> scrape token from display modal before close.

    Returns JSON: {ok, pit, scopes_ticked, name, level, error?}.
    """
    ctx = await get_context(session=GHL_SESSION, mode="headed")
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Navigate to private integrations
    settings_url = "https://app.gohighlevel.com/v2/settings/private-integrations"
    try:
        await page.goto(settings_url, wait_until="load", timeout=30000)
        await wait_for_hydration(page, max_ms=10000)
    except Exception as e:
        return json.dumps({"ok": False, "error": f"nav failed: {e}"})

    # Click "Create New Integration" - try several common labels
    for label in ("Create New Integration", "Create Integration", "Add Integration", "+ Add"):
        if await click_by_text(page, label, role="button", timeout=2500):
            break
    else:
        # Fallback: agentic prompt
        rep = agentic_browser_prompt(
            message=f"ghl_create_pit could not find the 'Create New Integration' button on {settings_url}. Click it manually then reply 'done'.",
            session=GHL_SESSION, timeout=600,
        )
        if rep["status"] == "timeout":
            return json.dumps({"ok": False, "error": "create-button not found, no human reply"})

    await asyncio.sleep(2)

    # Fill name
    try:
        name_input = await page.query_selector("input[name='name'], input[placeholder*='Name'], input[placeholder*='name']")
        if name_input:
            await name_input.fill(name)
            await asyncio.sleep(0.5)
    except Exception:
        pass

    # Tick scopes
    ticked = 0
    if scopes == "all":
        # Find scope picker container - try common patterns
        for container_sel in (
            "[class*='scopes']", "[class*='Scopes']",
            "[data-testid*='scope']", "form", "[role='dialog']"
        ):
            ticked = await tick_all_checkboxes(page, container_sel, delay_range=(0.04, 0.12))
            if ticked > 5:
                break
    else:
        scope_list = [s.strip() for s in scopes.split(",")]
        for s in scope_list:
            cb = await page.query_selector(f"input[type='checkbox'][value='{s}']")
            if cb:
                checked = await cb.is_checked()
                if not checked:
                    await cb.click()
                    ticked += 1
                    await asyncio.sleep(0.1)

    await asyncio.sleep(1)

    # Submit
    submitted = False
    for label in ("Create Integration", "Create", "Submit", "Save"):
        if await click_by_text(page, label, role="button", timeout=2500):
            submitted = True
            break
    if not submitted:
        return json.dumps({"ok": False, "error": "submit button not found", "scopes_ticked": ticked})

    # Scrape token from modal - wait up to 8s
    for _ in range(16):
        await asyncio.sleep(0.5)
        modal_text = await extract_modal_text(page)
        if modal_text:
            import re
            m = re.search(r"pit-[0-9a-f-]{32,}", modal_text)
            if m:
                return json.dumps({
                    "ok": True, "pit": m.group(0),
                    "scopes_ticked": ticked, "name": name, "level": level,
                }, indent=2)

    return json.dumps({"ok": False, "error": "token modal not detected", "scopes_ticked": ticked}, indent=2)


@mcp.tool()
async def ghl_list_pits(level: str = "agency") -> str:
    """List existing Private Integration Tokens visible in current view.

    Reads names + created dates from the Private Integrations settings page.
    Returns JSON array.
    """
    ctx = await get_context(session=GHL_SESSION, mode="headed")
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()
    settings_url = "https://app.gohighlevel.com/v2/settings/private-integrations"
    await page.goto(settings_url, wait_until="load", timeout=30000)
    await wait_for_hydration(page, max_ms=8000)
    rows = await page.evaluate("""
() => {
  const out=[];
  document.querySelectorAll('tr, [role=row], [class*=integration-row]').forEach(r => {
    const t=(r.innerText||'').trim();
    if (t && t.length>3) out.push(t.slice(0,200));
  });
  return out;
}
""")
    return json.dumps({"level": level, "rows": rows or []}, indent=2)


@mcp.tool()
async def agentic_browser_send_prompt(message: str, session: str = "default",
                                       timeout: int = 600) -> str:
    """Post a message to #agentic-browser and wait for human reply.

    Used for 2FA pauses, captcha handoffs, manual-fallback offers.
    Returns JSON: {status, reply, elapsed_s}.
    """
    result = agentic_browser_prompt(message=message, session=session, timeout=timeout)
    return json.dumps(result, indent=2)

if __name__ == "__main__":
    mcp.run()
