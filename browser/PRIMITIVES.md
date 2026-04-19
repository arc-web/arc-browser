# skool-manager browser primitive contract

This module mirrors the primitive contract defined in `arc-browser/PRIMITIVES.md`.
Implementations are local (no cross-repo dependency) but the contract is shared
so agents can move between tools with a predictable surface.

## Shared primitives (generic)

- `navigate_ready(page, url, wait_for_selector=None, post_nav_ms=2000)` - SPA-safe nav
- `with_retry(coro_factory, attempts=3)` - exponential backoff wrapper

## Skool-hardcoded primitives

Skool-specific versions of the auth contract, pre-bound to `skool.com`:

- `skool_auto_login(page, force=False) -> {"status", "reason"}` - reads 1Password
  item "Skool", fills login form, verifies redirect. Idempotent.
- `skool_verify_auth(page) -> bool` - probes `skool.com/feed`, returns whether
  the session is authenticated.

If you later add a second managed community platform (Circle, Discourse, etc.),
add a parallel `<platform>_auto_login` / `<platform>_verify_auth` here rather
than generalizing - each platform has enough quirks that the hardcoded form
beats a recipe lookup.

## Why not import from arc-browser?

Intentional. arc-browser is a general-purpose MCP server for any site.
skool-manager's browser layer is Skool-tuned. Sharing code would force one
side to flex to the other's constraints. Sharing the contract is enough.
