"""
Site structure analyzer. Detects pagination, listings, auth walls, CF protection.
Returns agent-actionable hints as JSON.
"""
import re

PAGINATION_PATTERNS = [
    (r'[?&]page=\d+', 'page'),
    (r'[?&]p=\d+', 'p'),
    (r'[?&]offset=\d+', 'offset'),
    (r'/page/\d+', 'path-segment'),
]

CF_SIGNATURES = [
    "Just a moment...",
    "cf-browser-verification",
    "challenge-platform",
    "cdn-cgi/challenge",
]


async def analyze_site(page) -> dict:
    """
    Analyze page structure: pagination, listings, auth walls, CF.
    Returns JSON with agent_hints array.
    """
    url = page.url
    html = await page.content()

    pagination = _detect_pagination(html)
    listing = await _detect_listing(page)
    auth_wall = _detect_auth_wall(html)
    cf = any(s in html for s in CF_SIGNATURES)

    hints = []
    if pagination:
        hints.append(f"Pagination via '{pagination['param']}' - iterate ?{pagination['param']}=1,2,3...")
    if listing:
        hints.append(f"Listing: {listing['count']} items in '{listing['selector']}'")
    if auth_wall:
        hints.append("Login wall detected - call browser_auto_login() first")
    if cf:
        hints.append("Cloudflare protected - prefer FlareSolverr for bulk HTTP scraping")

    return {
        "url": url,
        "pagination": pagination,
        "listing": listing,
        "auth_wall": auth_wall,
        "cf_protected": cf,
        "agent_hints": hints,
    }


def _detect_pagination(html: str) -> dict | None:
    """Detect pagination patterns in HTML."""
    for pattern, param in PAGINATION_PATTERNS:
        if re.search(pattern, html):
            return {"param": param}

    # Look for rel=next links
    if re.search(r'rel=["\']next["\']', html, re.I):
        return {"param": "rel-next"}

    return None


async def _detect_listing(page) -> dict | None:
    """Detect the most common list/grid structure (likely a listing)."""
    return await page.evaluate("""() => {
        const candidates = [];
        for (const el of document.querySelectorAll('ul, ol, [class*="list"], [class*="grid"], [class*="items"], tbody')) {
            if (el.children.length >= 3) {
                const cls = el.className.split(' ')[0] || '';
                candidates.push({
                    selector: cls ? `${el.tagName.toLowerCase()}.${cls}` : el.tagName.toLowerCase(),
                    count: el.children.length,
                });
            }
        }
        if (!candidates.length) return null;
        candidates.sort((a, b) => b.count - a.count);
        return candidates[0];
    }""")


def _detect_auth_wall(html: str) -> bool:
    """Detect login walls or auth requirements."""
    checks = [
        r'input[^>]*password',
        r'sign in to continue',
        r'log in to view',
        r'please log in',
    ]
    return any(re.search(p, html, re.I) for p in checks)
