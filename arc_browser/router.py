"""
One-shot task classifier. Runs at task submission, not mid-task.
Uses site_registry.json for known domains; falls back to conservative defaults.
"""
import json
from pathlib import Path
from urllib.parse import urlparse

_REGISTRY = json.loads(
    (Path(__file__).parent / "config" / "site_registry.json").read_text()
)

# Sites where even Patchright isn't enough - need real Chrome via CDP
_CDP_REQUIRED = {"linkedin.com", "twitter.com", "x.com", "facebook.com"}

# Scraping keywords that indicate data extraction intent
SCRAPING_KEYWORDS = {
    "scrape", "crawl", "extract", "collect", "harvest",
    "list all", "get all", "fetch all", "iterate", "pull data",
    "find all", "enumerate", "gather", "mine", "bulk", "all pages",
}


def _domain_of(url_or_domain: str) -> str:
    if "://" in url_or_domain:
        try:
            return urlparse(url_or_domain).netloc.lstrip("www.")
        except Exception:
            return url_or_domain
    return url_or_domain.lstrip("www.")


def get_recipe(url_or_domain: str) -> dict:
    """Return the full registry entry (recipe) for a URL or bare domain. {} if unknown."""
    return _REGISTRY.get(_domain_of(url_or_domain), {})


def classify(url: str, needs_extensions: bool = False, task: str = "") -> dict:
    """
    Classify a URL and return execution parameters.
    Called once at task submission - execution proceeds without further gates.
    task: optional task description to detect scraping intent and CF routing hints.
    """
    try:
        domain = urlparse(url).netloc.lstrip("www.")
    except Exception:
        domain = url

    entry = _REGISTRY.get(domain, {})
    risk = entry.get("risk", "medium")
    rate_limit = entry.get("actions_per_hour", 25)

    # Determine mode
    if domain in _CDP_REQUIRED:
        mode = "cdp"
    elif entry.get("mode"):
        mode = entry["mode"]
    elif needs_extensions:
        mode = "headed"
    elif risk == "low":
        mode = "headless"
    else:
        mode = "headed"

    disruptive = mode == "cdp"

    # Scraping intent + CF detection
    cf_protected = entry.get("cf_protected", False)
    task_lower = task.lower()
    is_scraping = any(kw in task_lower for kw in SCRAPING_KEYWORDS)
    use_fs = is_scraping and cf_protected

    return {
        "domain": domain,
        "risk": risk,
        "mode": mode,
        "disruptive": disruptive,
        "rate_limit": rate_limit,
        "cf_protected": cf_protected,
        "is_scraping": is_scraping,
        "use_flaresolverr": use_fs,
        "flaresolverr_hint": (
            f"{domain} is CF-protected and this looks like a scraping task. "
            f"FlareSolverr at http://187.77.222.191:8191/v1 is safer - "
            f"docs: ~/ai/infra/paperclip/docs/flaresolverr.md"
        ) if use_fs else None,
        "warning": (
            f"CDP mode required for {domain}. This connects to your real Chrome "
            f"and will interrupt your current browsing. "
            f"Use browser_task_confirmed() to proceed."
        ) if disruptive else None,
    }
