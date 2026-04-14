"""
Browser context factory. Supports 4 modes:
  headed   - Patchright + stealth, appears on second monitor (default)
  headless - For low-risk sites, no window
  vps      - Connects to Browserless on Hostinger via CDP
  cdp      - Connects to user's real running Chrome (most stealth, disruptive)
"""
import asyncio
import os
import signal
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))

from patchright.async_api import async_playwright
from playwright_stealth import stealth_async
from config.settings import SESSIONS_DIR, EXTENSIONS_DIR, SECOND_MONITOR_X, VPS_BROWSERLESS_URL

_sessions: dict = {}
_pw = None


def _kill_chrome_for_profile(profile_dir: str) -> None:
    """Kill any Chrome process using this user-data-dir, then clean up locks."""
    # Find Chrome processes with this profile's user-data-dir
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"--user-data-dir={profile_dir}"],
            capture_output=True, text=True, timeout=5
        )
        if result.stdout.strip():
            for pid_str in result.stdout.strip().split("\n"):
                try:
                    pid = int(pid_str.strip())
                    os.kill(pid, signal.SIGTERM)
                except (ValueError, OSError):
                    pass
            # Give Chrome a moment to exit cleanly
            import time
            time.sleep(0.5)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Clean up lock files
    for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        lock_path = os.path.join(profile_dir, lock_name)
        try:
            if os.path.islink(lock_path) or os.path.exists(lock_path):
                os.remove(lock_path)
        except OSError:
            pass


async def _get_pw():
    global _pw
    if not _pw:
        _pw = await async_playwright().start()
    return _pw


async def get_context(session: str = "default", mode: str = "headed", extensions: list = None):
    """
    Get or create a browser context for the named session.
    Returns existing context if alive; creates new one only if missing/dead.
    """
    ctx = _sessions.get(session)
    if ctx is not None:
        try:
            _ = ctx.pages
            return ctx
        except Exception:
            _sessions.pop(session, None)

    pw = await _get_pw()
    profile = os.path.join(SESSIONS_DIR, session)
    os.makedirs(profile, exist_ok=True)
    _kill_chrome_for_profile(profile)

    if mode == "headless":
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=profile,
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

    elif mode == "headed":
        args = [
            "--disable-blink-features=AutomationControlled",
            f"--window-position={SECOND_MONITOR_X},0",
            "--window-size=1920,1080",
            "--lang=en-US",
            "--no-first-run",
            "--disable-session-crashed-bubble",
            "--hide-crash-restore-bubble",
            "--suppress-message-center-popups",
        ]
        if extensions:
            ext_paths = [
                os.path.join(EXTENSIONS_DIR, e) if not os.path.isabs(e) else e
                for e in extensions
            ]
            joined = ",".join(ext_paths)
            args += [
                f"--disable-extensions-except={joined}",
                f"--load-extension={joined}",
            ]
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir=profile,
            headless=False,
            channel="chrome",
            args=args,
        )

    elif mode == "vps":
        if not VPS_BROWSERLESS_URL:
            raise ValueError("VPS_BROWSERLESS_URL not set in .env")
        browser = await pw.chromium.connect_over_cdp(VPS_BROWSERLESS_URL)
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()

    elif mode == "cdp":
        browser = await pw.chromium.connect_over_cdp("ws://localhost:9222")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()

    else:
        raise ValueError(f"Unknown mode: {mode}. Use headed/headless/vps/cdp")

    if mode in ("headless", "headed"):
        ctx.on("page", lambda p: asyncio.ensure_future(stealth_async(p)))

    _sessions[session] = ctx
    return ctx


def current_page(session: str = "default"):
    """Return the last active page in the named session's context."""
    ctx = _sessions.get(session)
    if not ctx or not ctx.pages:
        raise RuntimeError(f"No browser context open for session '{session}'. Call get_context() first.")
    return ctx.pages[-1]


async def close_session(session: str = "default"):
    """Close and remove a specific session."""
    ctx = _sessions.pop(session, None)
    if ctx:
        try:
            await ctx.close()
        except Exception:
            pass


# -- Reusable primitives ------------------------------------------------------


async def with_retry(coro_factory, attempts: int = 3, backoff: float = 1.5):
    """Retry an awaitable with exponential backoff.

    coro_factory: callable returning a fresh coroutine each attempt (needed
    because coroutines can only be awaited once).
    """
    last_exc = None
    delay = 0.5
    for i in range(attempts):
        try:
            return await coro_factory()
        except Exception as e:
            last_exc = e
            if i < attempts - 1:
                await asyncio.sleep(delay)
                delay *= backoff
    raise last_exc


async def navigate_ready(page, url: str, wait_for_selector: str = None,
                         wait_until: str = "load", timeout: int = 60000,
                         post_nav_ms: int = 1000):
    """Navigate and wait for the page to be actually usable.

    - Uses wait_until="load" by default (SPAs never hit networkidle)
    - Optionally waits for a specific selector after load
    - Adds post_nav settle time for SPA hydration
    """
    await page.goto(url, wait_until=wait_until, timeout=timeout)
    if wait_for_selector:
        await page.wait_for_selector(wait_for_selector, timeout=timeout)
    if post_nav_ms:
        await asyncio.sleep(post_nav_ms / 1000)


async def auto_login(site_id: str, session: str = None, force: bool = False) -> dict:
    """Auto-login for a site using the registry recipe + 1Password.

    Returns {"status": "logged_in"|"already"|"failed", "reason": str}.
    Idempotent: returns "already" if the verify_url check passes without
    needing to re-authenticate (unless force=True).
    """
    from router import get_recipe
    from utils.credentials import get_credentials

    recipe = get_recipe(site_id)
    auth = recipe.get("auth") if recipe else None
    if not auth:
        return {"status": "failed", "reason": f"No auth recipe for '{site_id}'"}

    required = ["credential_item", "login_url", "verify_url"]
    missing = [k for k in required if k not in auth]
    if missing:
        return {"status": "failed", "reason": f"Recipe missing auth fields: {missing}"}

    mode = recipe.get("mode", "headed")
    sess = session or site_id.replace(".", "_")
    ctx = await get_context(session=sess, mode=mode)
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    # Probe existing session first
    if not force:
        try:
            await page.goto(auth["verify_url"], wait_until="load", timeout=30000)
            await asyncio.sleep(1)
            if auth.get("verify_not_contains", "") not in page.url:
                return {"status": "already", "reason": "Existing session is valid"}
        except Exception:
            pass

    # Fetch credentials
    try:
        creds = get_credentials(auth["credential_item"])
    except Exception as e:
        return {"status": "failed", "reason": f"Credential lookup failed: {e}"}
    if not creds.get("username") or not creds.get("password"):
        return {"status": "failed", "reason": "Credentials missing username/password"}

    # Fill form
    form = auth.get("form", {})
    try:
        await page.goto(auth["login_url"], wait_until="load", timeout=60000)
        await asyncio.sleep(2)
        email_sel = form.get("email_selector")
        pw_sel = form.get("password_selector")
        if not email_sel or not pw_sel:
            return {"status": "failed", "reason": "Recipe form selectors incomplete"}
        await page.wait_for_selector(email_sel, timeout=30000)
        await page.fill(email_sel, creds["username"])
        await asyncio.sleep(0.5)
        await page.wait_for_selector(pw_sel, timeout=10000)
        await page.fill(pw_sel, creds["password"])
        await asyncio.sleep(0.5)
        if form.get("submit") == "enter":
            await page.keyboard.press("Enter")
        elif form.get("submit_selector"):
            await page.click(form["submit_selector"])
        else:
            await page.keyboard.press("Enter")
    except Exception as e:
        return {"status": "failed", "reason": f"Form submission failed: {e}"}

    # Poll for redirect away from login
    for _ in range(30):
        await asyncio.sleep(2)
        if auth.get("verify_not_contains", "") not in page.url:
            return {"status": "logged_in", "reason": f"Redirected to {page.url}"}

    return {"status": "failed", "reason": "Did not redirect away from login page"}


async def verify_auth(site_id: str, session: str = None) -> dict:
    """Check whether the session for `site_id` is authenticated.

    Returns {"authenticated": bool, "reason": str}.
    """
    from router import get_recipe

    recipe = get_recipe(site_id)
    auth = recipe.get("auth") if recipe else None
    if not auth:
        return {"authenticated": False, "reason": f"No auth recipe for '{site_id}'"}

    mode = recipe.get("mode", "headed")
    sess = session or site_id.replace(".", "_")
    ctx = await get_context(session=sess, mode=mode)
    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    try:
        await page.goto(auth["verify_url"], wait_until="load", timeout=30000)
        await asyncio.sleep(1)
        if auth.get("verify_not_contains", "") in page.url:
            return {"authenticated": False, "reason": f"Redirected to login ({page.url})"}
        return {"authenticated": True, "reason": f"At {page.url}"}
    except Exception as e:
        return {"authenticated": False, "reason": f"Probe failed: {e}"}
