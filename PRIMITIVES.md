# arc-browser primitive contract

Any tool that automates a browser against a specific site should implement the
same primitives arc-browser does. This lets future agents move between sites
with a predictable surface area.

## The contract

### `inspect_existing_state(site_id, scope) -> {"resources", "checked", "recommendation"}`
Inspect existing resources before creating anything. Browser agents must use
the provider UI or API to list current accounts, organizations, projects,
clients, tokens, sessions, and other relevant resource containers first.

The response must include:

- exact resources found by name, ID, organization, URL, local state path, and
  status
- exact surfaces checked when no matching resource is found
- a recommendation to reuse, create, pause, or escalate, with consequence and
  tradeoff
- the human approval point for irreversible or sensitive changes

Creation tools must not silently create long-lived external resources. This is
especially important for Google Cloud projects, OAuth consent screens, OAuth
clients, API enablement, billing changes, and any client secret download.

### `navigate_ready(page, url, wait_for_selector=None, wait_until="load", post_nav_ms=1000)`
Navigate and wait until the page is usable. `networkidle` never resolves on SPAs
that hold open websockets (Skool, LinkedIn). Default to `load`, optionally wait
for a target selector, then settle for SPA hydration.

### `auto_login(site_id, force=False) -> {"status", "reason"}`
Pull credentials from 1Password (via `op`), fill the form, submit, verify redirect.
Must be **idempotent**: if the session is already valid, return `{"status": "already"}`
without touching the form. Only re-auth when `force=True` or the verify check fails.

### `verify_auth(site_id) -> {"authenticated", "reason"}`
Navigate to a known-logged-in URL, check the URL did not redirect to login.
Must be callable before any scraping work. If it returns `authenticated: False`,
the caller should run `auto_login` before proceeding.

### `with_retry(coro_factory, attempts=3, backoff=1.5)`
Exponential-backoff retry wrapper. Wrap anything that can transiently fail:
`page.evaluate`, `page.goto`, `page.click`. Network flakes, lock contention,
and Playwright driver hiccups should not bubble up as fatal errors.

## Recipe schema (site_registry.json)

```json
{
  "<domain>": {
    "risk": "low|medium|high",
    "mode": "headless|headed|cdp|vps",
    "actions_per_hour": 60,
    "waits": { "default": "load", "post_nav_ms": 1500 },
    "auth": {
      "login_url": "...",
      "credential_item": "<1Password item title>",
      "form": {
        "email_selector": "...",
        "password_selector": "...",
        "submit": "enter" | "<selector>"
      },
      "verify_url": "...",
      "verify_not_contains": "..."
    },
    "notes": "Anything a future agent should know about this site"
  }
}
```

## Tool-level surface

Every browser automation tool (arc-browser, skool-manager's browser layer,
future gmail-manager, etc.) should expose equivalents of:

- `*_navigate(url, wait_for_selector?)` - SPA-safe nav
- `*_inspect_existing_state(scope)` - report what exists before creation
- `*_auto_login(site_id)` - unattended auth
- `*_verify_auth(site_id)` - pre-flight check
- `*_introspect(url)` - what does this tool know about the site?

Concepts flow between tools. Code doesn't.
