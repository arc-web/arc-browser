"""
agentic_browser_prompt: post a pause prompt to Discord #agentic-browser and wait
for the human to respond. Used by 2FA pauses, captcha handoffs, and
manual-fallback offers.

Two unblock paths:
  1. Human posts any reply in #agentic-browser (poll Discord)
  2. Human creates /tmp/<session>_resume file

Returns reply text (first non-empty Discord reply after the prompt, or
"resume" if file flag used).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

DISCORD_AGENT_DIR = "/Users/home/ai/agents/comms/discord_agent"
DEFAULT_CHANNEL = "agentic-browser"
DEFAULT_TIMEOUT = 900  # 15 min


def _discord_send(message: str, channel: str = DEFAULT_CHANNEL) -> tuple[bool, Optional[str]]:
    """Send a message to the agentic-browser channel via discord_agent. Returns (ok, posted_message_id)."""
    if DISCORD_AGENT_DIR not in sys.path:
        sys.path.insert(0, DISCORD_AGENT_DIR)
    try:
        from discord_api import DiscordClient  # type: ignore
    except Exception as e:
        return False, f"discord_api import failed: {e}"
    try:
        c = DiscordClient("arc")
        ch_id = c.resolve_channel(channel)
        ok = c.send_message(ch_id, message)
        return bool(ok), None
    except Exception as e:
        return False, f"send_message failed: {e}"


def _discord_poll_replies(after_ts: float, channel: str = DEFAULT_CHANNEL, limit: int = 20) -> list[dict]:
    """Return messages newer than after_ts in the channel."""
    if DISCORD_AGENT_DIR not in sys.path:
        sys.path.insert(0, DISCORD_AGENT_DIR)
    try:
        from discord_api import DiscordClient  # type: ignore
    except Exception:
        return []
    try:
        c = DiscordClient("arc")
        ch_id = c.resolve_channel(channel)
        msgs = c.get_messages(ch_id, limit=limit) or []
    except Exception:
        return []
    out = []
    for m in msgs:
        # Discord timestamp is ISO; convert
        ts_str = m.get("timestamp", "")
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()
        except Exception:
            continue
        if ts > after_ts and not m.get("author", {}).get("bot"):
            out.append({"ts": ts, "author": m["author"].get("username"), "content": m.get("content", "")})
    return sorted(out, key=lambda x: x["ts"])


def agentic_browser_prompt(
    message: str,
    session: str = "default",
    channel: str = DEFAULT_CHANNEL,
    timeout: int = DEFAULT_TIMEOUT,
    poll_interval: int = 10,
) -> dict:
    """Post `message` to #agentic-browser. Wait for human reply.

    Returns {"status": "replied"|"file_resume"|"timeout", "reply": str, "elapsed_s": int}.
    """
    start = time.time()
    body = f"```\n{message}\n```\n_Session: `{session}` - reply in this channel or create `/tmp/{session}_resume` to unblock._"
    ok, err = _discord_send(body, channel)
    if not ok:
        print(f"[agentic_browser_prompt] discord post failed: {err}", file=sys.stderr)

    resume_file = Path(f"/tmp/{session}_resume")
    deadline = start + timeout
    while time.time() < deadline:
        # File flag wins
        if resume_file.exists():
            try:
                content = resume_file.read_text().strip()
            except Exception:
                content = ""
            try:
                resume_file.unlink()
            except Exception:
                pass
            return {"status": "file_resume", "reply": content or "resume", "elapsed_s": int(time.time() - start)}
        # Poll Discord
        replies = _discord_poll_replies(start, channel=channel, limit=10)
        if replies:
            r = replies[-1]
            return {"status": "replied", "reply": r["content"], "elapsed_s": int(time.time() - start), "author": r["author"]}
        time.sleep(poll_interval)

    return {"status": "timeout", "reply": "", "elapsed_s": int(time.time() - start)}
