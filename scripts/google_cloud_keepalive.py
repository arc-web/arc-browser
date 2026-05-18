"""Open a saved Google Cloud OAuth arc-browser session and keep it alive."""
import argparse
import asyncio
import os
import signal
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


STOP = False


def _stop(_signum, _frame):
    global STOP
    STOP = True


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True)
    parser.add_argument("--duration", type=int, default=1800)
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [repo_root, env["PYTHONPATH"]] if env.get("PYTHONPATH") else [repo_root]
    )

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "arc_browser.server"],
        env=env,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "browser_google_cloud_resume",
                {"session": args.session},
            )
            for item in result.content:
                text = getattr(item, "text", None)
                if text:
                    print(text, flush=True)
            for _ in range(args.duration):
                if STOP:
                    break
                await asyncio.sleep(1)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
