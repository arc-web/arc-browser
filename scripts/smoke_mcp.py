"""Smoke-test the arc-browser MCP server over stdio."""
import argparse
import asyncio
import os
import sys

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--navigate",
        help="Optionally run browser_navigate against this URL after MCP startup.",
    )
    args = parser.parse_args()

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

            tools = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools.tools)
            print(f"tools={len(tool_names)}")
            print("has_browser_preflight=" + str("browser_preflight" in tool_names))
            print("has_browser_camofox_health=" + str("browser_camofox_health" in tool_names))
            print("has_browser_google_cloud_prepare_oauth=" + str("browser_google_cloud_prepare_oauth" in tool_names))
            print("has_browser_google_cloud_status=" + str("browser_google_cloud_status" in tool_names))
            print("has_browser_google_cloud_resume=" + str("browser_google_cloud_resume" in tool_names))

            preflight = await session.call_tool(
                "browser_preflight",
                {"url": "https://github.com"},
            )
            print("browser_preflight=https://github.com")
            for item in preflight.content:
                text = getattr(item, "text", None)
                if text:
                    print(text)

            camofox = await session.call_tool("browser_camofox_health", {})
            print("browser_camofox_health=")
            for item in camofox.content:
                text = getattr(item, "text", None)
                if text:
                    print(text)

            if args.navigate:
                nav = await session.call_tool(
                    "browser_navigate",
                    {"url": args.navigate, "session": "smoke"},
                )
                print("browser_navigate=")
                for item in nav.content:
                    text = getattr(item, "text", None)
                    if text:
                        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
