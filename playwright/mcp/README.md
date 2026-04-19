# Playwright MCP Server - Natural Language Browser Automation

Control browser automation with natural language through Cursor! State persists across all commands. You provide simple instructions, and Cursor AI handles all the advanced reasoning about how to execute them.

## ✅ Installation Complete

```bash
cd /Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp
npm install  # ✅ Done
npm run build  # ✅ Done
```

## 🎯 Configuration

Added to `/Users/home/aimacpro/7_tools/mcp_tools/mcp_config.json`:

```json
{
  "playwright": {
    "command": "node",
    "args": ["/Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp/dist/server.js"],
    "env": {
      "BROWSER_STATE_DIR": "/Users/home/aimacpro/.browser-states",
      "HEADLESS": "false"
    }
  }
}
```

**Restart Cursor** to activate the MCP server!

## 🚀 Usage Examples

### Basic Navigation & Interaction

```
You: Navigate to https://slack.com and click the "Sign in" button

Cursor AI: [Reasons about task, selects browser_execute tool, executes]
Result: ✅ Navigated to Slack, clicked sign in button, state saved
```

### Fill Forms

```
You: Fill the email field with "john@example.com" and click submit

Cursor AI: [Reasons about form filling, selects browser_execute tool, executes]
Result: ✅ Email filled, submit clicked, state persists
```

### Multi-Step Workflows (State Persists!)

```
You: Go to https://api.slack.com/apps/A09SMEFF7KR/oauth

Cursor AI: [Reasons about navigation, uses browser_execute, saves state]

You: Click "Add an OAuth Scope"

Cursor AI: [Reasons about continuing on same page, uses browser_execute, state persists]

You: Select "channels:history" from the dropdown

Cursor AI: [Reasons about dropdown selection, uses browser_execute, state saved - still logged in for next command!]
```

### Extract Data

```
You: Navigate to https://example.com and extract all text from h1 elements

Cursor AI: [Reasons about data extraction, uses browser_execute with extract parameter]
Result: {
  "h1": ["Example Domain", "Welcome"]
}
```

### Take Screenshots

```
You: Go to https://example.com and take a screenshot

Cursor AI: [Reasons about screenshot need, uses browser_execute with screenshot: true]
Result: Returns base64 screenshot data
```

### Manage State

```
You: Check browser state status

Cursor AI: [Reasons about state checking, uses browser_state tool with action: "status"]
Result: {
  "hasPersistedState": true,
  "currentUrl": "https://slack.com/..."
}
```

```
You: Clear browser state (logout)

Cursor AI: [Reasons about state clearing, uses browser_state with action: "clear"]
Result: State cleared, next command starts fresh
```

## 🧠 Natural Language Understanding

The server parses natural language into Playwright actions:

| You Say | Server Understands |
|---------|-------------------|
| "Click the login button" | `page.click('button:has-text("login")')` |
| "Fill username with john@example.com" | `page.fill('input[name*="username"]', 'john@example.com')` |
| "Go to https://example.com" | `page.goto('https://example.com')` |
| "Select Premium from dropdown" | `page.selectOption('select', 'Premium')` |
| "Wait 5 seconds" | `page.waitForTimeout(5000)` |
| "Take a screenshot" | `page.screenshot()` |

## 🔧 Available Tools

### `browser_execute`

Execute browser automation with natural language.

**Parameters**:
- `task` (required): Natural language description
- `url` (optional): Starting URL
- `waitFor` (optional): CSS selector to wait for
- `extract` (optional): Array of CSS selectors to extract data
- `screenshot` (optional): Take screenshot after execution

**Examples**:
```json
{
  "task": "Click the login button and fill email with test@example.com"
}

{
  "task": "Navigate to pricing page",
  "url": "https://example.com",
  "screenshot": true
}

{
  "task": "Extract product names",
  "extract": [".product-name", ".price"]
}
```

### `browser_state`

Manage browser state (cookies, auth, localStorage).

**Parameters**:
- `action` (required): "save" | "clear" | "status"

**Examples**:
```json
{
  "action": "status"
}

{
  "action": "clear"
}
```

## 💾 State Persistence

**State Storage**: `/Users/home/aimacpro/.browser-states/mcp-browser-state.json`

**What's Saved**:
- Cookies
- localStorage
- sessionStorage
- Authentication tokens
- Current page URL

**State Lifecycle**:
1. First command: Fresh browser, no state
2. Command executes: State saved automatically
3. Next command: State loaded, browser continues from where it left off
4. All subsequent commands: State persists!

**Benefits**:
- ✅ Login once, stay logged in
- ✅ Maintain session across multiple commands
- ✅ Resume workflows seamlessly
- ✅ No re-authentication needed

## 🎨 Complex Workflow Example

```
# Day 1: Setup Slack OAuth
You: Navigate to https://api.slack.com/apps/A09SMEFF7KR/oauth
Cursor AI: ✅ Done [State saved]

You: Click "Add an OAuth Scope"
Cursor AI: ✅ Done [Still on page, state persists]

You: Select "channels:history"
Cursor AI: ✅ Done [State saved]

You: Select "chat:write"
Cursor AI: ✅ Done [State saved]

# Day 2: Continue from where you left off
You: Check browser state
Cursor AI: Still at Slack OAuth page, logged in ✅

You: Click "Install to Workspace"
Cursor AI: ✅ Done [State persists]
```

## 🔍 Debugging

### View Server Logs

Server logs go to stderr, visible in MCP inspector or terminal:
```
🚀 Playwright MCP Server running
   State directory: /Users/home/aimacpro/.browser-states
   Headless: false
🌐 Browser launched
📄 New page created
🎯 Parsed intent: interaction (confidence: 0.90)
📋 Actions: 1
✅ Executed: click
💾 Browser state saved
```

### Check State File

```bash
cat /Users/home/aimacpro/.browser-states/mcp-browser-state.json
```

### Test Directly

```bash
node /Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp/dist/server.js
# Expects MCP protocol on stdin/stdout
```

## ⚙️ Configuration Options

### Environment Variables

- `BROWSER_STATE_DIR`: Where to save state files (default: `./.mcp-browser-state`)
- `HEADLESS`: Run browser headless (default: `true`, set to `false` to see browser)

### Headless vs Headed Mode

**Headed** (`HEADLESS=false`): See browser window, good for debugging
**Headless** (`HEADLESS=true`): Background execution, faster, good for production

## 🐛 Troubleshooting

### Browser won't start?

```bash
# Install Playwright browsers
cd /Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp
npx playwright install chromium
```

### State not persisting?

Check state directory exists and is writable:
```bash
ls -la /Users/home/aimacpro/.browser-states/
```

### Cursor can't find the tool?

1. Verify MCP config: `cat /Users/home/aimacpro/7_tools/mcp_tools/mcp_config.json`
2. Restart Cursor completely
3. Check MCP server list in Cursor settings

### Server crashes?

Check logs in Cursor MCP inspector, or run manually:
```bash
node dist/server.js 2>&1 | tee server.log
```

## 📚 Advanced Usage

### Custom Selectors

```
You: Click the button with data-testid "submit-btn"
# Server will try: button[data-testid="submit-btn"]
```

### Complex Forms

```
You: Fill email with john@example.com, fill password with secret123, and click submit
# Server parses into 3 separate actions
```

### Wait for Elements

```
You: Click login and wait for the dashboard to load
# Use waitFor parameter for specific element
{
  "task": "Click login",
  "waitFor": ".dashboard-container"
}
```

## 🎯 Next Steps

1. **Restart Cursor** to load the MCP server
2. **Try a simple command**: "Navigate to https://example.com"
3. **Build complex workflows** with persistent state
4. **Automate repetitive tasks** with natural language

---

**Status**: ✅ Installed and configured
**State**: Persistent across all commands
**Integration**: Ready to use in Cursor conversations
