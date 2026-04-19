# Browser Automation Orchestration Guide

**Date**: 2025-01-14
**Purpose**: Guide for orchestrating Puppeteer, Playwright, and Browser-Use tools

---

## Overview

This guide explains how to select and use the three browser automation tools available in this project:
1. **Puppeteer MCP** - Direct programmatic browser control
2. **Playwright MCP** - Conversational browser automation with state persistence
3. **Browser-Use** - Fully autonomous AI-driven browser tasks

---

## Tool Selection Decision Matrix

### Puppeteer MCP

**Best For**:
- Quick, deterministic tasks
- Screenshots and visual verification
- JavaScript execution in browser context
- Form automation with known selectors
- Simple navigation tasks

**Access Method**:
- Native MCP via Claude Code
- Command: Available as MCP tool in Claude Code
- Configuration: `~/.claude.json` or Claude Desktop config

**When to Use**:
- ✅ Need deterministic, scripted automation
- ✅ Quick one-off tasks
- ✅ Screenshot capture
- ✅ JavaScript evaluation
- ✅ Simple form filling

**Example Use Cases**:
```python
# Via Claude Code MCP:
# "Take a screenshot of example.com"
# "Execute JavaScript: document.title"
# "Navigate to github.com and screenshot the header"
```

---

### Playwright MCP

**Best For**:
- Multi-step workflows
- Stateful browser sessions
- Natural language browser control
- Complex navigation with state persistence
- Conversational automation

**Access Method**:
- Custom MCP server (HTTP/WebSocket)
- Native flag: `--play` or `--playwright` (Claude Code)
- Server: `4_agents/browser_automation_agent/playwright/mcp/`

**When to Use**:
- ✅ Need persistent sessions (cookies, auth)
- ✅ Complex multi-step workflows
- ✅ Natural language task execution
- ✅ State persistence across sessions
- ✅ Conversational control

**Example Use Cases**:
```python
# Via Claude Code:
# "Navigate to Slack and configure OAuth scopes"
# "Fill out the login form and save the session"
# "Complete the multi-step registration process"
```

**Server Startup**:
```bash
cd 4_agents/browser_automation_agent/playwright/mcp
MCP_TRANSPORT=http MCP_PORT=3000 node dist/server.js
```

---

### Browser-Use

**Best For**:
- Fully autonomous tasks
- Complex multi-step workflows requiring AI decision-making
- Tasks where you don't know the exact steps
- LLM-driven browser automation
- Production automation workflows

**Access Method**:
- Python agent with MCP tool provider
- Location: `7_tools/mcp_tools/integrations/browser_use_mcp/`
- Requires: LLM API key (OpenAI, Anthropic, etc.)

**When to Use**:
- ✅ Need fully autonomous execution
- ✅ Complex tasks requiring AI decision-making
- ✅ Don't know exact steps beforehand
- ✅ Production automation workflows
- ✅ Scheduled/background tasks

**Example Use Cases**:
```python
from browser_use import Agent
from browser_use_mcp.browser_use_tool_provider import BrowserUseToolProvider

# Initialize with MCP tools
tool_provider = BrowserUseToolProvider(mcp_server_url='http://localhost:3000')
tools = await tool_provider.get_tools()

# Create autonomous agent
agent = Agent(
    task="Navigate to example.com, extract all links, and create a report",
    llm="gpt-4o",
    tools=tools
)

result = await agent.run()
```

---

## Orchestration Patterns

### Pattern 1: Sequential Tool Usage

**Use Case**: Complex workflow requiring different tools at different stages

```
Task → Puppeteer (quick check) → Playwright (complex workflow) → Browser-Use (autonomous completion)
```

**Example**:
1. Use Puppeteer to quickly verify page loads
2. Use Playwright for stateful navigation and form filling
3. Use Browser-Use for autonomous completion of remaining steps

**Implementation**:
```python
# Step 1: Quick verification with Puppeteer (via Claude Code MCP)
# "Take a screenshot of example.com to verify it loads"

# Step 2: Complex workflow with Playwright
# "Navigate to example.com, fill the form, and save the session"

# Step 3: Autonomous completion with Browser-Use
agent = Agent(
    task="Complete the remaining steps autonomously",
    tools=playwright_mcp_tools
)
```

---

### Pattern 2: Parallel Tool Usage

**Use Case**: Multiple independent tasks that can run simultaneously

```
Task → [Puppeteer (screenshot) + Playwright (navigation) + Browser-Use (analysis)]
```

**Example**:
- Puppeteer: Capture screenshots of multiple pages
- Playwright: Navigate and interact with forms
- Browser-Use: Analyze page content

**Implementation**:
```python
import asyncio

async def parallel_tasks():
    # Run tasks in parallel
    results = await asyncio.gather(
        puppeteer_screenshot_task(),
        playwright_navigation_task(),
        browser_use_analysis_task()
    )
    return results
```

---

### Pattern 3: Fallback Chain

**Use Case**: Try multiple tools until one succeeds

```
Task → Browser-Use (try autonomous) → Playwright (if fails, conversational) → Puppeteer (if fails, direct)
```

**Example**:
1. Try Browser-Use for autonomous execution
2. If fails, fall back to Playwright for conversational control
3. If fails, fall back to Puppeteer for direct control

**Implementation**:
```python
async def execute_with_fallback(task):
    try:
        # Try Browser-Use first
        return await browser_use_agent.run(task)
    except Exception as e:
        try:
            # Fall back to Playwright
            return await playwright_mcp.execute(task)
        except Exception as e:
            # Fall back to Puppeteer
            return await puppeteer_mcp.execute(task)
```

---

## Tool Comparison Table

| Feature | Puppeteer MCP | Playwright MCP | Browser-Use |
|---------|---------------|----------------|-------------|
| **Access** | Native MCP | Custom Server / Native Flag | Python Agent |
| **Control Type** | Direct/Programmatic | Conversational | Autonomous |
| **State Persistence** | ❌ No | ✅ Yes | ✅ Yes (via MCP) |
| **Natural Language** | ❌ No | ✅ Yes | ✅ Yes |
| **LLM Required** | ❌ No | ❌ No | ✅ Yes |
| **Best For** | Quick tasks | Multi-step workflows | Complex autonomous tasks |
| **Setup Complexity** | Low | Medium | Medium |
| **Execution Speed** | Fast | Medium | Variable (LLM dependent) |
| **Deterministic** | ✅ Yes | ✅ Mostly | ⚠️ Variable |

---

## Integration Architecture

### Data Flow

```
┌─────────────────┐
│  User/System    │
│     Task        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Orchestrator   │ ◄─── Tool Selection Logic
│   (Phase 3.3)   │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────────┐
    │         │          │              │
    ▼         ▼          ▼              ▼
┌────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐
│Puppeteer│ │Playwright│ │Browser-Use│ │Fallback │
│   MCP   │ │   MCP    │ │   Agent   │ │  Chain   │
└────┬───┘ └────┬─────┘ └─────┬────┘ └────┬─────┘
     │          │              │           │
     └──────────┴──────────────┴───────────┘
                    │
                    ▼
            ┌───────────────┐
            │    Browser    │
            │  (Chromium)   │
            └───────────────┘
```

---

## Decision Flowchart

```
Start
  │
  ▼
Is task simple and deterministic?
  │ YES → Use Puppeteer MCP
  │ NO
  ▼
Does task require state persistence?
  │ YES → Use Playwright MCP
  │ NO
  ▼
Does task require AI decision-making?
  │ YES → Use Browser-Use
  │ NO
  ▼
Use Playwright MCP (default for complex tasks)
```

---

## Best Practices

### 1. Tool Selection
- **Start Simple**: Try Puppeteer first for quick tasks
- **Add Complexity**: Use Playwright for stateful workflows
- **Go Autonomous**: Use Browser-Use for complex AI-driven tasks

### 2. State Management
- **Playwright**: Use for persistent sessions (cookies, auth)
- **Browser-Use**: Inherits state from Playwright MCP
- **Puppeteer**: Start fresh each time (no state persistence)

### 3. Error Handling
- **Implement Fallback**: Try alternative tools if primary fails
- **Log Errors**: Track which tool failed and why
- **Retry Logic**: Use orchestrator for automatic retries

### 4. Performance
- **Puppeteer**: Fastest for simple tasks
- **Playwright**: Good balance of speed and features
- **Browser-Use**: Variable speed (depends on LLM response time)

---

## Next Steps

1. ✅ Tool selection matrix documented
2. ✅ Orchestration patterns defined
3. ⏭️ Implement orchestrator component (Phase 3.3)
4. ⏭️ Create example workflows (Phase 3.4)

---

**Document Generated**: 2025-01-14
**Status**: Complete
**Next Phase**: Orchestrator Component Implementation

