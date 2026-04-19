# Phase 4: Playwright MCP - Test Plan (Server Not Connected)

**MCP Status**: ❌ Not Showing in `claude mcp list`
**Expected Capability**: Browser automation & testing
**Server File**: ✓ Exists at configured path (11KB)

---

## Expected Tools

- `launch_browser` - Start browser instance
- `navigate` - Go to URL
- `click` - Click elements
- `type` - Input text
- `screenshot` - Capture page
- `get_content` - Extract page HTML
- `close_browser` - Cleanup

---

## Test Plan

### 1. Browser Launch
```javascript
// Launch headless Chrome
browser = await playwright.launch_browser({
  browser: "chromium",
  headless: true
})
// Expected: Browser ID, launch time <2s
```

**Validation**: Browser process started, no errors

---

### 2. Navigation & Content
```javascript
// Navigate to test page
await playwright.navigate({
  browser_id: <id>,
  url: "https://example.com"
})
// Expected: Load time <5s

// Get page content
content = await playwright.get_content({
  browser_id: <id>
})
// Expected: HTML containing "Example Domain"
```

---

### 3. Screenshots
```javascript
// Capture page
screenshot = await playwright.screenshot({
  browser_id: <id>,
  path: "test_data/screenshots/example_com_<timestamp>.png",
  fullPage: true
})
// Expected: File created, size >0, time <1s
```

**Storage**: `/Users/home/aimacpro/9-tests2026/mcp_testing/test_data/screenshots/`

---

### 4. Interactions (if available)
```javascript
// Test form interaction on httpbin.org
await playwright.navigate({
  url: "https://httpbin.org/forms/post"
})

await playwright.type({
  selector: 'input[name="custname"]',
  text: "MCP Test"
})

await playwright.click({
  selector: 'button[type="submit"]'
})
```

---

### 5. Cleanup
```javascript
// Close browser
await playwright.close_browser({
  browser_id: <id>
})

// Verify no orphan processes
// ps aux | grep chrome
```

---

## Performance Targets

| Operation | Target |
|-----------|--------|
| Browser launch | <2s |
| Page navigation | <5s |
| Screenshot | <1s |
| Element interaction | <500ms |
| Browser close | <1s |

---

## Test Scenarios

### Scenario 1: Basic Automation
```
1. Launch → example.com → screenshot → close
   Duration: ~8s
   Validation: Screenshot contains expected content
```

### Scenario 2: Multi-Page
```
1. Launch → page1 → screenshot
2. Navigate → page2 → screenshot
3. Close
   Validation: Both screenshots captured
```

---

## Current Issue

**Problem**: Server not appearing in MCP list
**Possible Causes**:
- Server startup failure
- Missing Node dependencies
- Environment configuration issue
- Protocol version mismatch

**Diagnostic Steps**:
1. Test manual server start: `node /Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp/dist/server.js`
2. Check for error output
3. Verify Node version compatibility
4. Check package.json dependencies

---

**Test Status**: ❌ Blocked - Server Not Connected
**Est. Duration**: 15-20 min (when functional)
