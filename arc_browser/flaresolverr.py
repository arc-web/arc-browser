"""
FlareSolverr HTTP client.
Solves Cloudflare challenges and converts cookies to Playwright format.
"""
import requests

FLARESOLVERR_URL = "http://187.77.222.191:8191/v1"
DEFAULT_TIMEOUT_MS = 60000


def solve_cf(url: str, session_id: str = None, timeout_ms: int = DEFAULT_TIMEOUT_MS) -> dict:
    """
    POST to FlareSolverr, return solution dict.

    Returns dict with keys: cookies, userAgent, response, url
    """
    payload = {"cmd": "request.get", "url": url, "maxTimeout": timeout_ms}
    if session_id:
        payload["session"] = session_id

    r = requests.post(FLARESOLVERR_URL, json=payload, timeout=timeout_ms / 1000 + 10)
    r.raise_for_status()
    data = r.json()

    if data.get("status") != "ok":
        raise RuntimeError(f"FlareSolverr: {data.get('message', 'unknown error')}")

    return data["solution"]


def to_playwright_cookies(solution: dict) -> list[dict]:
    """Convert FlareSolverr cookie list to Playwright add_cookies() format."""
    out = []
    for c in solution.get("cookies", []):
        entry = {
            "name": c["name"],
            "value": c["value"],
            "domain": c.get("domain", ""),
            "path": c.get("path", "/"),
        }
        for opt in ("expires", "httpOnly", "secure", "sameSite"):
            if opt in c:
                entry[opt] = c[opt]
        out.append(entry)
    return out


def check_health() -> bool:
    """Probe FlareSolverr health endpoint."""
    try:
        r = requests.get(FLARESOLVERR_URL.replace("/v1", "/"), timeout=5)
        return r.status_code == 200
    except Exception:
        return False
