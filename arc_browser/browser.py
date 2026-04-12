"""
Browser context factory. Supports 4 modes:
  headed   - Patchright + stealth, appears on second monitor (default)
  headless - For low-risk sites, no window
  vps      - Connects to Browserless on Hostinger via CDP
  cdp      - Connects to user's real running Chrome (most stealth, disruptive)
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from patchright.async_api import async_playwright
from playwright_stealth import stealth_async
from config.settings import SESSIONS_DIR, EXTENSIONS_DIR, SECOND_MONITOR_X, VPS_BROWSERLESS_URL

_sessions: dict = {}
_pw = None


def _clear_stale_lock(profile_dir: str) -> None:
    lock_path = os.path.join(profile_dir, "SingletonLock")
    if not os.path.islink(lock_path) and not os.path.exists(lock_path):
        return
    try:
        target = os.readlink(lock_path)
        pid_str = target.rsplit("-", 1)[-1]
        pid = int(pid_str)
        os.kill(pid, 0)
    except (OSError, ValueError, IndexError):
        try:
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
    _clear_stale_lock(profile)

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
