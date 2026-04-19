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
import time

from patchright.async_api import async_playwright
from playwright_stealth import stealth_async
from .settings import SESSIONS_DIR, EXTENSIONS_DIR, SECOND_MONITOR_X, VPS_BROWSERLESS_URL

_sessions: dict = {}
_pw = None


def _kill_chrome_for_profile(profile_dir: str) -> None:
    """Kill any Chrome process using this user-data-dir, then clean up locks."""
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
            time.sleep(0.5)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

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
    """Get or create a browser context for the named session."""
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
        raise RuntimeError(f"No browser context for session '{session}'. Navigate first.")
    return ctx.pages[-1]


async def close_session(session: str = "default"):
    """Close and remove a specific session."""
    ctx = _sessions.pop(session, None)
    if ctx:
        try:
            await ctx.close()
        except Exception:
            pass


# -- Reusable primitives (mirror arc-browser PRIMITIVES.md contract) -------


async def with_retry(coro_factory, attempts: int = 3, backoff: float = 1.5):
    """Retry an awaitable with exponential backoff."""
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
                         post_nav_ms: int = 2000):
    """Navigate and wait for the page to be actually usable (SPA-safe)."""
    await page.goto(url, wait_until=wait_until, timeout=timeout)
    if wait_for_selector:
        await page.wait_for_selector(wait_for_selector, timeout=timeout)
    if post_nav_ms:
        await asyncio.sleep(post_nav_ms / 1000)


# Skool-hardcoded auth primitives. Same contract as arc-browser's, but
# pre-bound to Skool specifics - no recipe lookup needed.

SKOOL_LOGIN_URL = "https://www.skool.com/login"
SKOOL_VERIFY_URL = "https://www.skool.com/feed"
SKOOL_EMAIL_SELECTOR = 'input[type="email"], input[name="email"]'
SKOOL_PASSWORD_SELECTOR = 'input[type="password"], input[name="password"]'


async def skool_verify_auth(page) -> bool:
    """Navigate to Skool feed and confirm we're logged in."""
    try:
        await page.goto(SKOOL_VERIFY_URL, wait_until="load", timeout=30000)
        await asyncio.sleep(2)
        if "skool.com/login" in page.url:
            return False
        text = await page.evaluate("() => document.body.innerText")
        if isinstance(text, str) and "Log in" in text and "Members" not in text:
            return False
        return True
    except Exception:
        return False


async def skool_auto_login(page, force: bool = False) -> dict:
    """Auto-login to Skool using credentials from 1Password item 'Skool'.

    Returns {"status": "logged_in"|"already"|"failed", "reason": str}.
    Idempotent: checks existing session first unless force=True.
    """
    from .credentials import get_skool_credentials

    if not force and await skool_verify_auth(page):
        return {"status": "already", "reason": "Existing session is valid"}

    try:
        creds = get_skool_credentials()
    except Exception as e:
        return {"status": "failed", "reason": f"Credential lookup failed: {e}"}
    if not creds.get("username") or not creds.get("password"):
        return {"status": "failed", "reason": "Credentials missing"}

    try:
        await page.goto(SKOOL_LOGIN_URL, wait_until="load", timeout=60000)
        await asyncio.sleep(2)
        if "skool.com/login" not in page.url:
            return {"status": "already", "reason": "Already logged in (redirect)"}

        await page.wait_for_selector(SKOOL_EMAIL_SELECTOR, timeout=30000)
        await page.fill(SKOOL_EMAIL_SELECTOR, creds["username"])
        await asyncio.sleep(0.5)
        await page.wait_for_selector(SKOOL_PASSWORD_SELECTOR, timeout=10000)
        await page.fill(SKOOL_PASSWORD_SELECTOR, creds["password"])
        await asyncio.sleep(0.5)
        await page.keyboard.press("Enter")

        for _ in range(30):
            await asyncio.sleep(2)
            if "skool.com/login" not in page.url:
                return {"status": "logged_in", "reason": f"Redirected to {page.url}"}

        return {"status": "failed", "reason": "Did not redirect away from login"}
    except Exception as e:
        return {"status": "failed", "reason": f"Form submission failed: {e}"}
