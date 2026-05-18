# arc-browser Manual Fallback Protocol

When automation fails, arc-browser does NOT silently fall back to manual click-through. The agent always:

1. Posts a clear message to Discord `#agentic-browser` via `agentic_browser_prompt(...)`
2. Pauses execution
3. Offers the human the option to drive the failed step manually
4. Resumes only on explicit human reply (Discord message or `touch /tmp/<session>_resume`)

## Decision tree

```
Tool fails (selector miss, modal not detected, 2FA challenge, captcha, scope picker confused)
  |
  v
Post to #agentic-browser:
  "automation hit [X] on [URL].
   - reply 'manual' to take over click-by-click (window stays open)
   - reply 'retry' to attempt the macro again
   - reply 'skip' to abort
   - reply 'abort' to close the session"
  |
  +-- reply 'manual' -> agent surfaces step-by-step guidance, polls
  |                     for completion signal, then resumes downstream macros
  +-- reply 'retry'  -> re-run the same macro once with relaxed timing
  +-- reply 'skip'   -> return failure to caller, do not close session
  +-- reply 'abort'  -> teardown session + return failure
```

## Implementation rule

Manual fallback is a **first-class branch** in every macro tool, not a hidden default. Macros must:

- Wrap risky steps in try/except
- On failure, call `agentic_browser_prompt(message=..., session=...)`
- Branch on `result['reply']` content
- Document the expected reply vocabulary in the message itself

## Anti-pattern

```python
# WRONG - silent fallback
try:
    await click_create_button()
except Exception:
    pass  # hope the user clicks it
```

```python
# RIGHT - explicit human pause
try:
    if not await click_by_text(page, "Create Integration"):
        raise RuntimeError("button not found")
except Exception:
    rep = agentic_browser_prompt(
        message="Could not find 'Create Integration' button. Click it manually, then reply 'done', or reply 'abort' to cancel.",
        session=GHL_SESSION,
        timeout=600,
    )
    if rep["reply"].lower().strip() == "abort":
        return {"ok": False, "error": "user aborted"}
    # otherwise assume done, continue
```

## Default behavior settings

Per `~/.cache/arc-browser/config.json` (created on first run):

```json
{
  "manual_fallback_default": "ask",
  "ask_timeout_s": 600,
  "auto_fallback_after_failures": 3,
  "audit_log_retention_days": 30
}
```

- `manual_fallback_default`: `"ask"` (default, recommended), `"never"`, or `"always"`
- `auto_fallback_after_failures`: after this many consecutive macro failures, escalate to manual prompt automatically
