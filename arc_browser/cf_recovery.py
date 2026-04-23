"""
Cloudflare challenge detection + recovery via FlareSolverr.
"""
from .flaresolverr import solve_cf, to_playwright_cookies

CF_SIGNATURES = [
    "Just a moment...",
    "cf-browser-verification",
    "challenge-platform",
    "cdn-cgi/challenge",
    "Checking your browser",
    "DDoS protection by Cloudflare",
    "Enable JavaScript and cookies to continue",
]


def is_cf_challenge(html: str) -> bool:
    """Detect if page HTML is a Cloudflare challenge."""
    return any(sig in html for sig in CF_SIGNATURES)


async def recover_cf(page, url: str) -> bool:
    """
    If current page is a CF challenge: solve via FlareSolverr, inject cookies, retry.

    Returns True if recovery ran.
    Returns False if no challenge detected (normal case).
    Raises RuntimeError if challenge persists after recovery.
    """
    html = await page.content()
    if not is_cf_challenge(html):
        return False

    # Solve challenge via FlareSolverr
    solution = solve_cf(url)
    cookies = to_playwright_cookies(solution)

    # Inject cookies and retry
    await page.context.add_cookies(cookies)
    await page.goto(url, wait_until="load", timeout=60000)

    # Verify challenge is gone
    html = await page.content()
    if is_cf_challenge(html):
        raise RuntimeError(f"CF challenge persists after FlareSolverr recovery for {url}")

    return True
