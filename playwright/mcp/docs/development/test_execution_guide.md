# Playwright MCP Test Suite - Execution Guide

**Purpose**: Step-by-step guide to execute the comprehensive test suite

**Estimated Time**: 15-20 minutes
**Prerequisites**: MCP server configured and Claude Code restarted

---

## Pre-Test Checklist

Before starting, verify:

- [ ] **MCP Server Built**: `npm run build` completed successfully
- [ ] **MCP Configuration**: `.mcp.json` contains `playwright-automation` server
- [ ] **Claude Code Restarted**: After MCP config changes
- [ ] **Browser State Directory**: `.browser-states/` exists
- [ ] **Playwright Installed**: Chromium browser available
- [ ] **Network Access**: Can access test URLs (example.com, google.com, github.com, slack.com)

### Quick Verification Commands

```bash
# Check MCP server is built
ls -la /Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp/dist/server.js

# Check MCP configuration
cat /Users/home/aimacpro/.mcp.json | grep playwright-automation

# Check state directory
ls -la /Users/home/aimacpro/.browser-states/

# Verify Playwright browsers installed
npx playwright --version
```

---

## Test Execution Method

**Option 1: Manual Execution** (Recommended for first run)
- Execute each test sequentially using Claude Code
- Document results in real-time
- Best for understanding behavior and debugging

**Option 2: Automated Script** (Future)
- Create test runner script
- Execute all tests programmatically
- Best for regression testing

---

## Test Execution Steps

### Test 1: Basic Navigation & State Initialization

**Command to Claude**:
```
Use the browser_execute tool to navigate to https://example.com and take a screenshot. Tell me what you see on the page.
```

**Expected MCP Tool Call**:
```json
{
  "name": "browser_execute",
  "arguments": {
    "task": "Navigate to https://example.com",
    "url": "https://example.com",
    "screenshot": true
  }
}
```

**Validation**:
- ✅ Response includes `success: true`
- ✅ `currentUrl` is `https://example.com`
- ✅ `pageTitle` is "Example Domain"
- ✅ `screenshot` field contains base64 image data
- ✅ State file created: `.browser-states/mcp-browser-state.json`

**Record Results**: ✅ PASS / ❌ FAIL

---

### Test 2: State Persistence Check

**Command to Claude**:
```
Check the browser state status. Is there any persisted state from previous sessions?
```

**Expected MCP Tool Call**:
```json
{
  "name": "browser_state",
  "arguments": {
    "action": "status"
  }
}
```

**Validation**:
- ✅ Response includes `success: true`
- ✅ `hasPersistedState` is `true` (after Test 1)
- ✅ `currentUrl` is present

**Record Results**: ✅ PASS / ❌ FAIL

---

### Test 3: Complex Navigation with State

**Command to Claude**:
```
Go to https://slack.com and click the "Sign in" button. Then check the browser state again to confirm cookies and session data are being saved.
```

**Expected MCP Tool Calls**:
1. First call:
```json
{
  "name": "browser_execute",
  "arguments": {
    "task": "Go to https://slack.com and click the Sign in button",
    "url": "https://slack.com"
  }
}
```

2. Second call:
```json
{
  "name": "browser_state",
  "arguments": {
    "action": "status"
  }
}
```

**Validation**:
- ✅ Navigation succeeds
- ✅ Sign in button clicked (may navigate to login page)
- ✅ State check shows `hasPersistedState: true`
- ✅ State file contains cookies for slack.com

**Record Results**: ✅ PASS / ❌ FAIL

---

### Test 4: Form Interaction

**Command to Claude**:
```
Navigate to https://www.google.com, fill the search box with "Playwright automation", press Enter, and extract all the h3 headings from the results page.
```

**Expected MCP Tool Call**:
```json
{
  "name": "browser_execute",
  "arguments": {
    "task": "Fill the search box with 'Playwright automation' and press Enter",
    "url": "https://www.google.com",
    "extract": ["h3"]
  }
}
```

**Validation**:
- ✅ Navigation to Google succeeds
- ✅ Search box filled correctly
- ✅ Enter key pressed (form submitted)
- ✅ Results page loaded
- ✅ H3 headings extracted and returned in `data` field

**Record Results**: ✅ PASS / ❌ FAIL

---

### Test 5: Multi-Step Workflow (CRITICAL TEST)

**Execute as 4 separate commands:**

**Command 1**:
```
Navigate to https://github.com/login
```

**Command 2** (separate, without navigating):
```
Check what page we're on without navigating - verify we're still on the GitHub login page
```

**Command 3** (separate):
```
Take a screenshot of the current page
```

**Command 4**:
```
Check browser state status
```

**Expected Results**:
- ✅ Command 1: Navigation succeeds, state saved
- ✅ Command 2: Still on `https://github.com/login` (state persisted!)
- ✅ Command 3: Screenshot shows GitHub login page
- ✅ Command 4: State status confirms persistence

**Critical Validation**:
- ✅ Browser context persists between separate commands
- ✅ No state loss between commands
- ✅ URL remains correct across commands

**Record Results**: ✅ PASS / ❌ FAIL

**Note**: If this test fails, state persistence is broken and needs immediate attention.

---

### Test 6: State Management

**Command 1**:
```
Save the current browser state explicitly
```

**Command 2**:
```
Check the state status to confirm it was saved successfully
```

**Expected MCP Tool Calls**:
1. `browser_state` with `action: "save"`
2. `browser_state` with `action: "status"`

**Validation**:
- ✅ Save action succeeds
- ✅ Status check confirms state exists
- ✅ State file updated

**Record Results**: ✅ PASS / ❌ FAIL

---

### Test 7: Error Handling

**Command to Claude**:
```
Try to click a non-existent element: Click the button with text 'ThisButtonDefinitelyDoesNotExist'
```

**Expected MCP Tool Call**:
```json
{
  "name": "browser_execute",
  "arguments": {
    "task": "Click the button with text 'ThisButtonDefinitelyDoesNotExist'"
  }
}
```

**Validation**:
- ✅ Error returned gracefully (not a crash)
- ✅ Response includes `success: false`
- ✅ `error` field contains helpful message
- ✅ `currentUrl` still present
- ✅ Browser state preserved (not corrupted)
- ✅ Can continue with next command

**Record Results**: ✅ PASS / ❌ FAIL

---

### Test 8: Performance & Response

**Command to Claude**:
```
Navigate to https://www.github.com and measure how quickly the MCP server responds. Tell me the current URL and page title.
```

**Expected MCP Tool Call**:
```json
{
  "name": "browser_execute",
  "arguments": {
    "task": "Navigate to https://www.github.com",
    "url": "https://www.github.com"
  }
}
```

**Validation**:
- ✅ Navigation completes
- ✅ Response includes `executionTimeMs` field
- ✅ `currentUrl` is `https://github.com` (or redirected URL)
- ✅ `pageTitle` is present
- ✅ Response time < 5 seconds

**Performance Targets**:
- Navigation: < 5 seconds ✅
- State save: < 500ms ✅
- Screenshot: < 2 seconds ✅

**Record Results**: ✅ PASS / ❌ FAIL
**Performance Metrics**: Record `executionTimeMs` value

---

### Test 9: Natural Language Understanding

**Command to Claude**:
```
Go to example.com, wait for 2 seconds, then take a screenshot and tell me the main heading text
```

**Expected MCP Tool Call**:
```json
{
  "name": "browser_execute",
  "arguments": {
    "task": "Go to example.com, wait for 2 seconds, then take a screenshot and tell me the main heading text",
    "url": "https://example.com",
    "extract": ["h1"],
    "screenshot": true
  }
}
```

**Validation**:
- ✅ Multi-step command parsed correctly
- ✅ Navigation to example.com succeeds
- ✅ 2-second wait executed
- ✅ Screenshot taken
- ✅ Main heading (h1) extracted and returned
- ✅ All actions executed in sequence

**Record Results**: ✅ PASS / ❌ FAIL

---

### Test 10: State Cleanup

**Command 1**:
```
Clear the browser state
```

**Command 2**:
```
Verify it was cleared by checking the state status
```

**Expected MCP Tool Calls**:
1. `browser_state` with `action: "clear"`
2. `browser_state` with `action: "status"`

**Validation**:
- ✅ Clear action succeeds
- ✅ Status check shows `hasPersistedState: false`
- ✅ State file removed or reset
- ✅ Next navigation starts fresh (no old cookies)

**Record Results**: ✅ PASS / ❌ FAIL

---

## Results Documentation Template

After completing all tests, fill out:

```markdown
## Test Results - [Date]

### Test Results Summary

| Test # | Test Name | Status | Notes | Performance |
|--------|-----------|--------|-------|-------------|
| 1 | Basic Navigation | PASS/FAIL | | |
| 2 | State Persistence Check | PASS/FAIL | | |
| 3 | Complex Navigation | PASS/FAIL | | |
| 4 | Form Interaction | PASS/FAIL | | |
| 5 | Multi-Step Workflow | PASS/FAIL | **CRITICAL** | |
| 6 | State Management | PASS/FAIL | | |
| 7 | Error Handling | PASS/FAIL | | |
| 8 | Performance | PASS/FAIL | | |
| 9 | Natural Language | PASS/FAIL | | |
| 10 | State Cleanup | PASS/FAIL | | |

### Performance Metrics

- Average navigation time: _____ seconds
- Average state save time: _____ milliseconds
- Average screenshot time: _____ seconds
- Average data extraction time: _____ seconds

### Grades

- **State Persistence**: A-F (_____)
- **Error Handling**: A-F (_____)
- **Natural Language Understanding**: A-F (_____)
- **Overall Integration**: A-F (_____)

### Issues Found

1. **Issue**: _____
   - **File**: _____
   - **Line**: _____
   - **Severity**: Critical/High/Medium/Low

### Recommendations

1. _____
2. _____
```

---

## Troubleshooting

### Issue: MCP Server Not Found

**Symptom**: Claude says "I don't have access to browser_execute tool"

**Solution**:
1. Verify `.mcp.json` configuration
2. Restart Claude Code completely
3. Check MCP server list in Claude settings

### Issue: Browser Won't Start

**Symptom**: Error about browser not found

**Solution**:
```bash
cd /Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp
npx playwright install chromium
```

### Issue: State Not Persisting

**Symptom**: Test 5 fails (multi-step workflow)

**Solution**:
1. Check state directory permissions: `ls -la .browser-states/`
2. Verify state file is being created
3. Check MCP server logs for errors
4. Review `browser-agent.ts` state save/load logic

### Issue: Natural Language Not Parsing

**Symptom**: Test 9 fails (multi-step command)

**Solution**:
1. Check intent parser logs (visible in MCP server stderr)
2. Try simpler command format
3. Use explicit `extract` parameter if needed

---

## Success Criteria

**Overall Test Suite PASS if**:
- ✅ Test 5 (Multi-Step Workflow) passes - **CRITICAL**
- ✅ At least 8/10 tests pass
- ✅ State Persistence Grade ≥ B
- ✅ Error Handling Grade ≥ B
- ✅ No critical issues found

**Overall Test Suite FAIL if**:
- ❌ Test 5 fails (state persistence broken)
- ❌ < 7/10 tests pass
- ❌ State Persistence Grade < C
- ❌ Critical issues found

---

## Next Steps After Testing

1. **If All Tests Pass**: Document results, mark as production-ready
2. **If Tests Fail**: Review `TEST_SUITE_ANALYSIS.md` for implementation gaps
3. **If Critical Issues**: Fix immediately before production use
4. **If Minor Issues**: Create enhancement tickets

---

**Ready to Execute**: ✅ All prerequisites met, enhancements implemented

**Test Suite Version**: 1.0
**Last Updated**: 2025-01-14
