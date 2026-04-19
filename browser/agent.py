"""
Autonomous browser agent using browser-use + local Ollama model.
"""
import os

from .settings import OLLAMA_MODEL, SESSIONS_DIR, SECOND_MONITOR_X

BEHAVIORAL_PREAMBLE = (
    "You are controlling a real browser. After each action, pause naturally "
    "before the next. Read page content before acting. Never rush. "
    "If you see a CAPTCHA, stop and report it - do not attempt to solve it. "
    "If a task is impossible, explain why clearly.\n\n"
)


async def run_task(task: str, session: str = "default", mode: str = "headed") -> str:
    """Run a natural language task autonomously using browser-use + Ollama."""
    from browser_use import Agent, BrowserSession
    from browser_use.llm import ChatOllama

    profile = os.path.join(SESSIONS_DIR, session)
    os.makedirs(profile, exist_ok=True)

    headless = mode == "headless"
    args = [
        "--disable-blink-features=AutomationControlled",
        f"--window-position={SECOND_MONITOR_X},0",
        "--window-size=1920,1080",
        "--lang=en-US",
    ]

    browser_session = BrowserSession(
        user_data_dir=profile,
        headless=headless,
        channel="chrome" if not headless else None,
        args=args,
    )

    llm = ChatOllama(model=OLLAMA_MODEL)
    agent = Agent(
        task=BEHAVIORAL_PREAMBLE + task,
        llm=llm,
        browser=browser_session,
    )

    result = await agent.run(max_steps=25)
    return result.final_result() or "Task completed (no text result returned)."
