"""
Camofox HTTP client.
Sidecar at jo-inc/camofox-browser - stealth Firefox (Camoufox) wrapped in REST API.
Use for sites where Patchright Chromium fingerprint is detected (Turnstile, Datadome).
"""
import os

import requests

CAMOFOX_URL = os.environ.get("CAMOFOX_URL", "http://127.0.0.1:9377")
CAMOFOX_KEY = os.environ.get("CAMOFOX_ACCESS_KEY")
DEFAULT_TIMEOUT = 60


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if CAMOFOX_KEY:
        h["Authorization"] = f"Bearer {CAMOFOX_KEY}"
    return h


def health() -> dict:
    r = requests.get(f"{CAMOFOX_URL}/health", headers=_headers(), timeout=5)
    r.raise_for_status()
    return r.json()


def check_health() -> bool:
    try:
        return health().get("ok") is True
    except Exception:
        return False


def open_tab(url: str, user_id: str = "default", session_key: str = "default") -> str:
    """Open tab, return tab_id. user_id = session owner; session_key = tab group."""
    r = requests.post(
        f"{CAMOFOX_URL}/tabs",
        headers=_headers(),
        json={"url": url, "userId": user_id, "sessionKey": session_key},
        timeout=DEFAULT_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["tabId"]


def navigate(tab_id: str, url: str, user_id: str = "default") -> dict:
    r = requests.post(
        f"{CAMOFOX_URL}/tabs/{tab_id}/navigate",
        headers=_headers(),
        params={"userId": user_id},
        json={"url": url},
        timeout=DEFAULT_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def snapshot(tab_id: str, user_id: str = "default", fmt: str = "json") -> dict:
    """Accessibility snapshot - ~90% smaller than raw HTML."""
    r = requests.get(
        f"{CAMOFOX_URL}/tabs/{tab_id}/snapshot",
        headers=_headers(),
        params={"userId": user_id, "format": fmt},
        timeout=DEFAULT_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def click(tab_id: str, ref: str, user_id: str = "default") -> dict:
    r = requests.post(
        f"{CAMOFOX_URL}/tabs/{tab_id}/click",
        headers=_headers(),
        params={"userId": user_id},
        json={"ref": ref},
        timeout=DEFAULT_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def type_text(tab_id: str, ref: str, text: str, submit: bool = False,
              user_id: str = "default") -> dict:
    r = requests.post(
        f"{CAMOFOX_URL}/tabs/{tab_id}/type",
        headers=_headers(),
        params={"userId": user_id},
        json={"ref": ref, "text": text, "submit": submit},
        timeout=DEFAULT_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def close_tab(tab_id: str, user_id: str = "default") -> None:
    requests.delete(
        f"{CAMOFOX_URL}/tabs/{tab_id}",
        headers=_headers(),
        params={"userId": user_id},
        timeout=DEFAULT_TIMEOUT,
    )
