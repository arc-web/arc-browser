# Browser Agent App Integrations

This directory contains browser automation plans, scripts, and utilities for specific applications and tools. These integrations demonstrate how apps can collaborate with the browser automation agent.

## Architecture

**Principle**: Apps/tools should call the browser agent to use browser automation tools, rather than maintaining their own browser automation code.

- **Browser Agent** (`4_agents/browser_automation_agent/`): Centralized browser automation capability
- **App Integrations** (this directory): App-specific browser automation plans and utilities
- **Apps/Tools**: Call browser agent APIs/tools to perform browser automation tasks

## Integrations

### Google Ads MCP
- **Plans**: 
  - `google_ads/browser_automation_plan.md` - Main browser automation plan
  - `google_ads/CREDENTIALS_COLLECTION_PLAN.md` - Credentials collection plan
  - `google_ads/README_AUTOMATION.md` - Automation documentation
  - `google_ads/AUTOMATION_READY.md` - Automation readiness status
- **Purpose**: Browser automation plans for collecting Google Ads API credentials
- **Usage**: Google Ads MCP server can call browser agent to execute these plans

### Google Drive MCP
- **Plan**: `google_drive/COMET_BROWSER_SETUP.md`
- **Purpose**: Browser automation guide for Google Drive OAuth setup
- **Usage**: Google Drive MCP server can call browser agent to execute this plan

### Reddit AI Assistant
- **Files**:
  - `reddit/playwright_reddit_extraction.md` - Playwright automation plan
  - `reddit/extract_reddit_credentials.py` - Credentials extraction script
- **Purpose**: Playwright automation for Reddit credential extraction
- **Usage**: Reddit AI Assistant app can call browser agent to execute this plan

### Image/Video MCP
- **Utility**: `image_video/src/utils/browser_key_fetcher.ts`
- **Purpose**: Browser automation utility for fetching API keys from various providers
- **Usage**: Image/Video MCP server can import and use this utility, which calls browser agent

## How Apps Use Browser Agent

Apps should integrate with the browser agent through:

1. **MCP Tools**: Use Playwright MCP tools (sole browser automation tool)
2. **API Calls**: Call Playwright MCP HTTP endpoints if running in server mode
3. **Direct Integration**: Import Playwright MCP utilities and orchestrate tasks

**Note**: Puppeteer MCP and Browser-Use have been deprecated. Use Playwright MCP only.

## Adding New Integrations

When creating browser automation for a new app:

1. Create a subdirectory under `app_integrations/` for your app
2. Add browser automation plans, scripts, or utilities
3. Document how the app should call the browser agent
4. Update this README with the new integration

## Example: App Calling Browser Agent

```python
# Example: Google Ads MCP calling browser agent
# Use Playwright MCP directly via MCP tools or HTTP API

# Via MCP tools (Claude Code):
# "Execute the browser automation plan in app_integrations/google_ads/browser_automation_plan.md"

# Via HTTP API:
import aiohttp

async def execute_plan(plan_path: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:3000/execute",
            json={
                "tool": "browser_execute",
                "arguments": {
                    "task": f"Execute plan from {plan_path}"
                }
            }
        ) as response:
            return await response.json()
```

