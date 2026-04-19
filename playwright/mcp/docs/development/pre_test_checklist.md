# Pre-Test Checklist - Playwright MCP Server

**Purpose**: Verify all prerequisites before executing test suite

**Date**: ___________
**Tester**: ___________

---

## ✅ Prerequisites Checklist

### 1. Build & Compilation

- [ ] **MCP Server Built**
  ```bash
  cd /Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp
  npm run build
  ```
  - [ ] Build completed without errors
  - [ ] `dist/server.js` exists
  - [ ] All TypeScript files compiled successfully

**Status**: ⬜ Not Started / ⬜ In Progress / ⬜ Complete / ⬜ Failed

**Notes**: _________________________________________________

---

### 2. MCP Configuration

- [ ] **MCP Server Configured**
  - [ ] Check `.mcp.json` file exists
  - [ ] `playwright-automation` server entry present
  - [ ] Correct path to `dist/server.js`
  - [ ] Environment variables set correctly:
    - [ ] `BROWSER_STATE_DIR` set to `/Users/home/aimacpro/.browser-states`
    - [ ] `HEADLESS` set to `false` (for visibility during testing)

**Configuration Check**:
```bash
cat /Users/home/aimacpro/.mcp.json | grep -A 10 playwright-automation
```

**Expected Output**:
```json
"playwright-automation": {
  "type": "stdio",
  "command": "node",
  "args": [
    "/Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp/dist/server.js"
  ],
  "env": {
    "BROWSER_STATE_DIR": "/Users/home/aimacpro/.browser-states",
    "HEADLESS": "false"
  }
}
```

**Status**: ⬜ Not Started / ⬜ In Progress / ⬜ Complete / ⬜ Failed

**Notes**: _________________________________________________

---

### 3. Claude Code Restart

- [ ] **Claude Code Restarted**
  - [ ] Closed Claude Code completely
  - [ ] Restarted Claude Code
  - [ ] MCP servers loaded (check settings)
  - [ ] `browser_execute` tool available
  - [ ] `browser_state` tool available

**Verification**:
- Ask Claude: "What MCP tools do you have available?"
- Should see `browser_execute` and `browser_state` in the list

**Status**: ⬜ Not Started / ⬜ In Progress / ⬜ Complete / ⬜ Failed

**Notes**: _________________________________________________

---

### 4. Browser State Directory

- [ ] **State Directory Exists**
  ```bash
  ls -la /Users/home/aimacpro/.browser-states/
  ```
  - [ ] Directory exists
  - [ ] Directory is writable
  - [ ] Can create files in directory

**Status**: ⬜ Not Started / ⬜ In Progress / ⬜ Complete / ⬜ Failed

**Notes**: _________________________________________________

---

### 5. Playwright Installation

- [ ] **Playwright Browsers Installed**
  ```bash
  npx playwright --version
  npx playwright install chromium
  ```
  - [ ] Playwright CLI available
  - [ ] Chromium browser installed
  - [ ] No installation errors

**Status**: ⬜ Not Started / ⬜ In Progress / ⬜ Complete / ⬜ Failed

**Notes**: _________________________________________________

---

### 6. Network Connectivity

- [ ] **Test URLs Accessible**
  - [ ] `https://example.com` accessible
  - [ ] `https://www.google.com` accessible
  - [ ] `https://github.com` accessible
  - [ ] `https://slack.com` accessible

**Quick Test**:
```bash
curl -I https://example.com
curl -I https://www.google.com
curl -I https://github.com
curl -I https://slack.com
```

**Status**: ⬜ Not Started / ⬜ In Progress / ⬜ Complete / ⬜ Failed

**Notes**: _________________________________________________

---

### 7. Dependencies Installed

- [ ] **Node Modules Installed**
  ```bash
  cd /Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp
  npm install
  ```
  - [ ] `node_modules/` directory exists
  - [ ] All dependencies installed
  - [ ] No installation errors

**Status**: ⬜ Not Started / ⬜ In Progress / ⬜ Complete / ⬜ Failed

**Notes**: _________________________________________________

---

### 8. Code Enhancements Applied

- [ ] **Recent Enhancements Built**
  - [ ] Enter key press support added
  - [ ] Multi-step command parsing enhanced
  - [ ] Page title extraction added
  - [ ] Performance metrics added
  - [ ] All changes compiled successfully

**Status**: ⬜ Not Started / ⬜ In Progress / ⬜ Complete / ⬜ Failed

**Notes**: _________________________________________________

---

### 9. Test Documentation Ready

- [ ] **Test Suite Documents Available**
  - [ ] `TEST_SUITE.md` exists
  - [ ] `TEST_EXECUTION_GUIDE.md` exists
  - [ ] `TEST_SUITE_ANALYSIS.md` exists
  - [ ] `PRE_TEST_CHECKLIST.md` (this file) exists

**Status**: ⬜ Not Started / ⬜ In Progress / ⬜ Complete / ⬜ Failed

**Notes**: _________________________________________________

---

### 10. Smoke Test (Optional but Recommended)

- [ ] **Quick Smoke Test**
  - [ ] Ask Claude: "Navigate to https://example.com"
  - [ ] Verify response includes `success: true`
  - [ ] Verify `currentUrl` is correct
  - [ ] Verify state file created

**Status**: ⬜ Not Started / ⬜ In Progress / ⬜ Complete / ⬜ Failed

**Notes**: _________________________________________________

---

## Quick Verification Script

Run this to verify everything quickly:

```bash
#!/bin/bash

echo "=== Playwright MCP Pre-Test Verification ==="
echo ""

echo "1. Checking build..."
if [ -f "/Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp/dist/server.js" ]; then
  echo "   ✅ Build exists"
else
  echo "   ❌ Build missing - run: npm run build"
fi

echo ""
echo "2. Checking MCP config..."
if grep -q "playwright-automation" /Users/home/aimacpro/.mcp.json; then
  echo "   ✅ MCP config found"
else
  echo "   ❌ MCP config missing"
fi

echo ""
echo "3. Checking state directory..."
if [ -d "/Users/home/aimacpro/.browser-states" ]; then
  echo "   ✅ State directory exists"
else
  echo "   ⚠️  State directory missing (will be created automatically)"
fi

echo ""
echo "4. Checking Playwright..."
if command -v npx &> /dev/null; then
  echo "   ✅ npx available"
else
  echo "   ❌ npx not found"
fi

echo ""
echo "5. Checking network..."
if curl -s --head https://example.com | head -n 1 | grep -q "200 OK"; then
  echo "   ✅ Network accessible"
else
  echo "   ❌ Network issues"
fi

echo ""
echo "=== Verification Complete ==="
```

---

## Final Checklist

Before starting test execution:

- [ ] All prerequisites checked ✅
- [ ] All issues resolved
- [ ] Claude Code restarted
- [ ] Test documentation reviewed
- [ ] Ready to execute Test 1

**Ready to Proceed**: ⬜ Yes / ⬜ No

**Blockers** (if any):
1. _________________________________________________
2. _________________________________________________
3. _________________________________________________

---

## Sign-Off

**Pre-Test Checklist Completed By**: ___________

**Date**: ___________

**Status**: ⬜ Ready for Testing / ⬜ Issues Found (see blockers above)

---

**Next Step**: Proceed to `TEST_EXECUTION_GUIDE.md` to begin test execution.
