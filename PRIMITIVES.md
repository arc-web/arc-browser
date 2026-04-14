# ghost-browser primitive contract

Any tool that automates a browser against a specific site should implement the
same primitives ghost-browser does. This lets future agents move between sites
with a predictable surface area.

## The contract

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

Every browser automation tool (ghost-browser, skool-manager's browser layer,
future gmail-manager, etc.) should expose equivalents of:

- `*_navigate(url, wait_for_selector?)` - SPA-safe nav
- `*_auto_login(site_id)` - unattended auth
- `*_verify_auth(site_id)` - pre-flight check
- `*_introspect(url)` - what does this tool know about the site?

Concepts flow between tools. Code doesn't.
