"""
One-shot URL classifier. Determines browser mode, risk level, and rate limits.
"""
import json
from pathlib import Path
from urllib.parse import urlparse

_REGISTRY = json.loads(
    (Path(__file__).parent / "site_registry.json").read_text()
)

_CDP_REQUIRED = {"linkedin.com", "twitter.com", "x.com", "facebook.com"}


def classify(url: str, needs_extensions: bool = False) -> dict:
    """Classify a URL and return execution parameters."""
    try:
        domain = urlparse(url).netloc.lstrip("www.")
    except Exception:
        domain = url

    entry = _REGISTRY.get(domain, {})
    risk = entry.get("risk", "medium")
    rate_limit = entry.get("actions_per_hour", 25)

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

    return {
        "domain": domain,
        "risk": risk,
        "mode": mode,
        "disruptive": disruptive,
        "rate_limit": rate_limit,
        "warning": (
            f"CDP mode required for {domain}. This connects to your real Chrome "
            f"and will interrupt your current browsing. "
            f"Use browser_task_confirmed() to proceed."
        ) if disruptive else None,
    }
