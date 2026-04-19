# Quick Start Guide: Browser Automation

**⚠️ DEPRECATION NOTICE**: Puppeteer MCP and Browser-Use have been deprecated. **Use Playwright MCP only.**

See [DEPRECATION_NOTICE.md](../DEPRECATION_NOTICE.md) for details.

---

## Overview

**This project uses Playwright MCP as the sole browser automation tool.**

**Playwright MCP provides**:
- ✅ Comprehensive stealth mode (bypasses bot detection)
- ✅ State persistence (maintains sessions)
- ✅ Natural language interface
- ✅ LLM-powered autonomous tasks
- ✅ Error recovery & anti-spazzing

---

## Quick Start: Puppeteer MCP

### Prerequisites
- Claude Code with MCP configured
- Puppeteer MCP added to `.claude.json`

### Usage
Simply use Claude Code and ask:
```
"Take a screenshot of example.com"
"Navigate to github.com and execute: document.title"
"Fill the search box on example.com with 'test'"
```

### Available Tools
- `puppeteer_navigate` - Navigate to URLs
- `puppeteer_screenshot` - Capture screenshots
- `puppeteer_evaluate` - Execute JavaScript
- `puppeteer_click` - Click elements
- `puppeteer_fill` - Fill form fields
- `puppeteer_select` - Select dropdown options
- `puppeteer_hover` - Hover over elements

---

## Quick Start: Playwright MCP

### Prerequisites
```bash
cd 4_agents/browser_automation_agent/playwright/mcp
npm install
npm run build
```

### Start Server
```bash
MCP_TRANSPORT=http MCP_PORT=3000 node dist/server.js
```

### Usage via HTTP
```python
import aiohttp

async def execute_task(task: str):
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:3000/execute",
            json={"tool": "browser_execute", "arguments": {"task": task}}
        ) as response:
            return await response.json()
```

### Usage via Claude Code
Use `--play` or `--playwright` flag, or configure in `.mcp.json`

### Available Tools
- `browser_execute` - Execute natural language browser tasks
- `browser_state` - Manage browser state (save, load, status, clear)

---

## Quick Start: Browser-Use (LEADER)

**Browser-Use is the primary autonomous browser tool** - use it for complex tasks where you don't know the exact steps.

### Configuration (Already Done)
Added to `mcp_config.json` and applied to all tools:
```json
"browser-use": {
  "command": "/Users/home/.local/bin/uvx",
  "args": ["mcp-browser-use"],
  "env": {}
}
```

### Usage via Claude Code
Simply ask Claude to do autonomous browser tasks:
```
"Go to Airtable, log in, and create a new base called 'Projects'"
"Navigate to Slack OAuth settings and add the channels:history scope"
"Find the cheapest flight from SF to NYC on Google Flights"
```

### How It Works
- Uses Claude as the LLM brain (no separate API key needed!)
- Claude decides what actions to take autonomously
- State persists across commands

### Available Tools
- `browser_use` - Execute autonomous browser tasks with AI decision-making

### Legacy Python Integration (Optional)
For advanced Python workflows, see `7_tools/mcp_tools/integrations/browser_use_mcp/`

---

## Quick Start: Orchestrator

### Prerequisites
- All three tools set up (see above)

### Usage
```python
from browser_automation_orchestrator import BrowserAutomationOrchestrator

orchestrator = BrowserAutomationOrchestrator()

# Simple task (auto-selects Puppeteer)
result = await orchestrator.execute_task("Take a screenshot of example.com")

# Stateful task (auto-selects Playwright)
result = await orchestrator.execute_task(
    "Navigate to example.com and save session",
    require_state_persistence=True
)

# Autonomous task (auto-selects Browser-Use)
result = await orchestrator.execute_task(
    "Extract all links from example.com",
    autonomous=True
)
```

---

## Tool Selection Guide

### When to Use Puppeteer
- ✅ Quick screenshots
- ✅ Simple navigation
- ✅ JavaScript execution
- ✅ Deterministic tasks

### When to Use Playwright
- ✅ Multi-step workflows
- ✅ Stateful sessions
- ✅ Natural language control
- ✅ Persistent authentication

### When to Use Browser-Use
- ✅ Fully autonomous tasks
- ✅ Complex workflows
- ✅ AI-driven decision making
- ✅ Production automation

---

## Examples

See `7_tools/mcp_tools/examples/orchestration/` for complete examples:
- `simple_automation.py` - Puppeteer example
- `conversational_workflow.py` - Playwright example
- `autonomous_task.py` - Browser-Use example
- `hybrid_workflow.py` - Multiple tools together
- `slack_oauth_setup.py` - Real-world example

---

## Troubleshooting

### Puppeteer MCP Not Available
- Check `.claude.json` configuration
- Restart Claude Code
- Verify MCP connection: `claude mcp list`

### Playwright MCP Server Won't Start
- Check port 3000 is available: `lsof -i :3000`
- Verify dependencies: `npm install`
- Check build: `npm run build`

### Browser-Use Import Errors
- Activate virtual environment: `source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Check Python version: `python --version` (requires 3.8+)

---

## Next Steps

1. Read `BROWSER_AUTOMATION_ORCHESTRATION.md` for detailed guide
2. Explore example workflows in `examples/orchestration/`
3. Review test results in `SMOKE_TEST_RESULTS.md`
4. Use orchestrator for unified API

---

**Last Updated**: 2025-01-14
**Status**: Ready for use

