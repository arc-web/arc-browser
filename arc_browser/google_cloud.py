"""Google Cloud Console OAuth setup helpers for arc-browser."""
import json
import time
from pathlib import Path


STATE_DIR = Path.home() / ".arc-browser" / "google-cloud-oauth"

SERVICE_API_IDS = {
    "gmail": ["gmail.googleapis.com"],
    "drive": ["drive.googleapis.com"],
    "gtm": ["tagmanager.googleapis.com"],
    "analytics": ["analyticsdata.googleapis.com", "analytics.googleapis.com"],
    "google-ads": ["googleads.googleapis.com"],
    "search-console": ["searchconsole.googleapis.com"],
    "gmb": [
        "mybusinessaccountmanagement.googleapis.com",
        "mybusinessbusinessinformation.googleapis.com",
    ],
    "youtube": ["youtube.googleapis.com"],
    "calendar": ["calendar-json.googleapis.com"],
    "people": ["people.googleapis.com"],
}

GOOGLE_CLOUD_SELECTORS = {
    "project_selector": "a[href*='projectselector'], button[aria-label*='project'], cfc-project-switcher",
    "api_search": "input[aria-label*='Search'], input[placeholder*='Search']",
    "enable_button": "button:has-text('Enable'), button[aria-label*='Enable']",
    "consent_screen": "a[href*='/apis/credentials/consent'], a[href*='oauthconsent']",
    "credentials_create": "button:has-text('Create credentials'), button[aria-label*='Create credentials']",
    "oauth_client_id": "text='OAuth client ID'",
    "application_type": "mat-select[aria-label*='Application type'], select[aria-label*='Application type']",
    "desktop_app": "text='Desktop app'",
    "download_json": "a:has-text('Download JSON'), button:has-text('Download JSON')",
}

SENSITIVE_BLOCKERS = {
    "login": ["accounts.google.com", "signin", "sign in"],
    "captcha": ["captcha", "recaptcha", "verify you are human"],
    "billing": ["billing account", "enable billing", "payment profile"],
    "terms": ["terms of service", "accept the terms", "agreement"],
    "consent": ["grant access", "authorize", "allow access", "choose an account"],
    "download_confirmation": ["download your client configuration", "client secret"],
}


def parse_services(services: str | list[str]) -> list[str]:
    if isinstance(services, list):
        raw_items = services
    else:
        raw_items = services.split(",")
    keys = []
    for item in raw_items:
        key = item.strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def api_ids_for_services(service_keys: list[str]) -> list[str]:
    api_ids = []
    for key in service_keys:
        for api_id in SERVICE_API_IDS.get(key, []):
            if api_id not in api_ids:
                api_ids.append(api_id)
    return api_ids


def state_path(session: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "-" for ch in session)
    return STATE_DIR / f"{safe}.json"


def save_state(session: str, payload: dict) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = state_path(session)
    path.write_text(json.dumps(payload, indent=2))
    return path


def read_state(session: str) -> dict | None:
    path = state_path(session)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def stable_urls(project_id: str, api_ids: list[str]) -> dict:
    project_arg = f"?project={project_id}" if project_id else ""
    return {
        "project_selector": "https://console.cloud.google.com/projectselector2/home/dashboard",
        "api_library": [
            f"https://console.developers.google.com/apis/api/{api_id}/overview?project={project_id}"
            for api_id in api_ids
        ] if project_id else [],
        "consent_screen": f"https://console.cloud.google.com/apis/credentials/consent{project_arg}",
        "credentials": f"https://console.cloud.google.com/apis/credentials{project_arg}",
        "oauth_clients": f"https://console.cloud.google.com/auth/clients{project_arg}",
    }


def build_prepare_packet(account: str, services: str | list[str], project_policy: str,
                         project_id: str, session: str) -> dict:
    service_keys = parse_services(services)
    api_ids = api_ids_for_services(service_keys)
    urls = stable_urls(project_id, api_ids)
    start_url = urls["credentials"] if project_id else urls["project_selector"]
    return {
        "tool": "browser_google_cloud_prepare_oauth",
        "status": "starting",
        "account": account,
        "session": session,
        "project_policy": project_policy,
        "project_id": project_id,
        "services": service_keys,
        "api_ids": api_ids,
        "start_url": start_url,
        "stable_urls": urls,
        "selectors": GOOGLE_CLOUD_SELECTORS,
        "steps": [
            "Select or confirm the Google Cloud project.",
            "Enable each required API from stable_urls.api_library.",
            "Confirm or create the OAuth consent screen.",
            "Create an OAuth client with application type Desktop app.",
            "Stop before downloading or revealing client secret JSON if human confirmation is required.",
        ],
        "handoff_reasons": list(SENSITIVE_BLOCKERS.keys()),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def classify_blocker(url: str, text: str) -> str | None:
    haystack = f"{url}\n{text}".lower()
    for name, patterns in SENSITIVE_BLOCKERS.items():
        if any(pattern in haystack for pattern in patterns):
            return name
    return None
