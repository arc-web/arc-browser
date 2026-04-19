# Playwright MCP Server - Comprehensive Test Suite

**Purpose**: Validate Playwright MCP server functionality, state persistence, and natural language understanding.

**Execution Time**: ~15-20 minutes total
**Test Coverage**: 10 comprehensive test scenarios

---

## Test 1: Basic Navigation & State Initialization

**Objective**: Verify basic navigation works and state is initialized correctly.

**Test Steps**:
1. Navigate to https://example.com
2. Take a screenshot
3. Report what you see on the page

**Expected Results**:
- ✅ Navigation succeeds
- ✅ Screenshot captured
- ✅ Page content visible (Example Domain page)
- ✅ State file created in `.browser-states/`

**Validation Criteria**:
- [ ] Navigation completed successfully
- [ ] Screenshot returned (base64 or file path)
- [ ] Page title/content reported correctly
- [ ] State file exists after navigation

---

## Test 2: State Persistence Check

**Objective**: Verify that persisted state from previous sessions can be detected.

**Test Steps**:
1. Check browser state status using `browser_state` tool with `action: "status"`
2. Report if any persisted state exists

**Expected Results**:
- ✅ State status check succeeds
- ✅ Reports whether state file exists
- ✅ Reports current URL if state exists
- ✅ Handles case where no state exists gracefully

**Validation Criteria**:
- [ ] State status tool responds correctly
- [ ] Correctly identifies existing state (if any)
- [ ] Handles no-state scenario without errors
- [ ] Returns structured JSON response

---

## Test 3: Complex Navigation with State

**Objective**: Verify state persistence across complex navigation and interactions.

**Test Steps**:
1. Navigate to https://slack.com
2. Click the "Sign in" button
3. Check browser state again to confirm cookies and session data are being saved

**Expected Results**:
- ✅ Navigation to Slack succeeds
- ✅ Sign in button clicked successfully
- ✅ State saved after interaction
- ✅ Cookies/session data present in state file

**Validation Criteria**:
- [ ] Navigation works
- [ ] Button click succeeds (may navigate to login page)
- [ ] State file updated with cookies
- [ ] State check confirms persistence

---

## Test 4: Form Interaction

**Objective**: Test form filling and data extraction capabilities.

**Test Steps**:
1. Navigate to https://www.google.com
2. Fill the search box with "Playwright automation"
3. Press Enter (submit search)
4. Extract all the h3 headings from the results page

**Expected Results**:
- ✅ Navigation to Google succeeds
- ✅ Search box located and filled
- ✅ Search submitted (Enter pressed)
- ✅ Results page loaded
- ✅ H3 headings extracted successfully

**Validation Criteria**:
- [ ] Form field identified correctly
- [ ] Text entered successfully
- [ ] Search executed
- [ ] Results page loaded
- [ ] Data extraction works (h3 elements found)
- [ ] Extracted data returned in structured format

---

## Test 5: Multi-Step Workflow (Critical Test)

**Objective**: Verify state persistence across separate commands without losing context.

**Test Steps**:
Execute this multi-step workflow to verify state persistence:

1. **First command**: Navigate to https://github.com/login
2. **Second command** (separate): Check what page we're on without navigating - verify we're still on the GitHub login page
3. **Third command** (separate): Take a screenshot of the current page
4. **Fourth command**: Check browser state status

**Expected Results**:
- ✅ First command: Navigation succeeds, state saved
- ✅ Second command: Still on GitHub login page (state persisted)
- ✅ Third command: Screenshot taken of GitHub login page
- ✅ Fourth command: State status confirms persistence

**Validation Criteria**:
- [ ] Browser context persists between separate commands
- [ ] No state loss between commands
- [ ] URL remains correct across commands
- [ ] Screenshot shows correct page
- [ ] State file updated after each command

**Critical Success Factor**: This test validates the core state persistence feature - if this fails, the MCP server is not working correctly.

---

## Test 6: State Management

**Objective**: Test explicit state save and status verification.

**Test Steps**:
1. Save the current browser state explicitly using `browser_state` tool with `action: "save"`
2. Check the state status to confirm it was saved successfully

**Expected Results**:
- ✅ Explicit save succeeds
- ✅ State status confirms save was successful
- ✅ State file updated with current browser state

**Validation Criteria**:
- [ ] Save action completes without errors
- [ ] State status reflects saved state
- [ ] State file contains current cookies/localStorage
- [ ] Timestamp or version info available (if implemented)

---

## Test 7: Error Handling

**Objective**: Verify graceful error handling for non-existent elements.

**Test Steps**:
1. Try to click a non-existent element: "Click the button with text 'ThisButtonDefinitelyDoesNotExist'"
2. Verify error handling works gracefully

**Expected Results**:
- ✅ Error caught gracefully
- ✅ Meaningful error message returned
- ✅ Browser state preserved (not corrupted)
- ✅ No crash or unhandled exception

**Validation Criteria**:
- [ ] Error returned in structured format
- [ ] Error message is helpful (mentions element not found)
- [ ] Browser state still valid after error
- [ ] Can continue with next command after error
- [ ] Error includes context (current URL, attempted action)

---

## Test 8: Performance & Response

**Objective**: Measure MCP server response time and verify performance.

**Test Steps**:
1. Navigate to https://www.github.com
2. Measure how quickly the MCP server responds
3. Report the current URL and page title

**Expected Results**:
- ✅ Navigation completes
- ✅ Response time measured (< 5 seconds for navigation)
- ✅ URL and title reported correctly

**Validation Criteria**:
- [ ] Response time acceptable (< 5s for navigation)
- [ ] URL reported correctly
- [ ] Page title extracted correctly
- [ ] Performance metrics logged

**Performance Targets**:
- Navigation: < 5 seconds
- State save: < 500ms
- Screenshot: < 2 seconds
- Data extraction: < 1 second

---

## Test 9: Natural Language Understanding

**Objective**: Test natural language parsing accuracy and multi-step command understanding.

**Test Steps**:
Use this natural language command: "Go to example.com, wait for 2 seconds, then take a screenshot and tell me the main heading text"

**Expected Results**:
- ✅ Navigation to example.com succeeds
- ✅ 2-second wait executed
- ✅ Screenshot taken
- ✅ Main heading text extracted and reported

**Validation Criteria**:
- [ ] Natural language parsed correctly
- [ ] Multiple actions in one command handled
- [ ] Wait duration parsed correctly
- [ ] Screenshot captured
- [ ] Text extraction works
- [ ] All actions executed in sequence

**Natural Language Patterns Tested**:
- Navigation: "Go to", "Navigate to"
- Timing: "wait for X seconds"
- Actions: "take a screenshot"
- Extraction: "tell me the main heading text"

---

## Test 10: State Cleanup

**Objective**: Verify state can be cleared and verified as cleared.

**Test Steps**:
1. Clear the browser state using `browser_state` tool with `action: "clear"`
2. Verify it was cleared by checking the state status

**Expected Results**:
- ✅ State cleared successfully
- ✅ State status confirms no persisted state
- ✅ State file removed or reset

**Validation Criteria**:
- [ ] Clear action succeeds
- [ ] State file removed or reset
- [ ] Status check confirms no state
- [ ] Next navigation starts fresh (no old cookies)

---

## Test Results Template

After completing all tests, provide:

### 1. Pass/Fail Results for Each Test

| Test # | Test Name | Status | Notes |
|--------|-----------|--------|-------|
| 1 | Basic Navigation | PASS/FAIL | |
| 2 | State Persistence Check | PASS/FAIL | |
| 3 | Complex Navigation | PASS/FAIL | |
| 4 | Form Interaction | PASS/FAIL | |
| 5 | Multi-Step Workflow | PASS/FAIL | |
| 6 | State Management | PASS/FAIL | |
| 7 | Error Handling | PASS/FAIL | |
| 8 | Performance | PASS/FAIL | |
| 9 | Natural Language | PASS/FAIL | |
| 10 | State Cleanup | PASS/FAIL | |

### 2. Performance Metrics

- **Response Times**:
  - Average navigation time: _____ seconds
  - Average state save time: _____ milliseconds
  - Average screenshot time: _____ seconds
  - Average data extraction time: _____ seconds

- **Delays Observed**:
  - Any unexpected delays: _____
  - Browser startup time: _____ seconds

### 3. State Persistence Grade (A-F)

**Grade**: _____

**Criteria**:
- **A**: State persists perfectly across all commands, no state loss
- **B**: State persists well, minor issues in edge cases
- **C**: State persists but occasional loss or corruption
- **D**: State persistence unreliable, frequent issues
- **F**: State does not persist, state lost between commands

**Notes**: _____

### 4. Error Handling Grade (A-F)

**Grade**: _____

**Criteria**:
- **A**: Graceful handling, helpful messages, state preserved
- **B**: Good handling, minor issues with error messages
- **C**: Errors handled but messages unclear or state sometimes lost
- **D**: Errors cause state corruption or unclear failures
- **F**: Crashes or unhandled exceptions

**Notes**: _____

### 5. Natural Language Understanding Grade (A-F)

**Grade**: _____

**Criteria**:
- **A**: Parses complex multi-step commands accurately
- **B**: Parses most commands correctly, minor misunderstandings
- **C**: Basic commands work, complex commands fail
- **D**: Frequent parsing errors, unclear intent
- **F**: Cannot parse natural language commands

**Notes**: _____

### 6. Overall Integration Grade (A-F)

**Grade**: _____

**Criteria**:
- **A**: Production-ready, all features work seamlessly
- **B**: Mostly ready, minor improvements needed
- **C**: Functional but needs significant improvements
- **D**: Major issues, not production-ready
- **F**: Critical failures, does not work

**Notes**: _____

### 7. Specific Issues Found

**Issues with Line Numbers/File References**:

1. **Issue**: _____
   - **File**: _____
   - **Line**: _____
   - **Severity**: Critical/High/Medium/Low
   - **Description**: _____

2. **Issue**: _____
   - **File**: _____
   - **Line**: _____
   - **Severity**: Critical/High/Medium/Low
   - **Description**: _____

### 8. Recommendations

**After comparing against**:
- Playwright official documentation
- MCP SDK best practices
- Research findings from `AI_BROWSER_AUTOMATION_RESEARCH_2025.md`
- Industry standards for browser automation

**Compare specifically against**:
- Browser-Use framework patterns
- Stagehand implementation approaches
- Playwright's official state management examples
- MCP server implementation guidelines

**Recommendations**:

1. **Critical**:
   - _____

2. **High Priority**:
   - _____

3. **Medium Priority**:
   - _____

4. **Low Priority**:
   - _____

5. **Enhancements**:
   - _____

---

## Execution Instructions

### Prerequisites

1. Playwright MCP server installed and built
2. MCP server configured in `.mcp.json`
3. Claude Code restarted to load MCP server
4. Browser state directory exists: `.browser-states/`

### Running Tests

Execute each test sequentially, documenting results as you go. Use the MCP tools:
- `browser_execute` for navigation and interactions
- `browser_state` for state management

### Test Environment

- **MCP Server**: `/Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp/dist/server.js`
- **State Directory**: `/Users/home/aimacpro/.browser-states/`
- **Browser**: Chromium (via Playwright)
- **Headless Mode**: false (for visibility during testing)

---

## Success Criteria Summary

**Overall Test Suite PASS if**:
- ✅ Test 5 (Multi-Step Workflow) passes - critical for state persistence
- ✅ At least 8/10 tests pass
- ✅ State Persistence Grade ≥ B
- ✅ Error Handling Grade ≥ B
- ✅ No critical issues found

**Overall Test Suite FAIL if**:
- ❌ Test 5 fails (state persistence broken)
- ❌ < 7/10 tests pass
- ❌ State Persistence Grade < C
- ❌ Critical issues found that prevent production use

---

**Test Suite Version**: 1.0
**Last Updated**: 2025-01-14
**Maintainer**: Browser Automation Team
