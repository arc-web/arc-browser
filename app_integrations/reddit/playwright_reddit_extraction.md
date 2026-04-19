# Ultra-Advanced Playwright Reddit Credential Extraction Plan

## OBJECTIVE
Extract Reddit API credentials (Client ID, Client Secret) from https://www.reddit.com/prefs/apps using Playwright automation with comprehensive error handling.

## OUTPUT
Save credentials to: `reddit_credentials.json` (NOT .env)

## EXECUTION PLAN

### Phase 1: Browser Initialization & Authentication Check
**Goal:** Start browser and verify Reddit login status

#### Step 1.1: Launch Browser with Persistence
```yaml
Action: Initialize Playwright browser with persistent context
Config:
  - headless: false (so user can see what's happening)
  - viewport: 1920x1080
  - userAgent: Real Chrome user agent
  - timeout: 60000ms
Error Handling:
  - If browser fails to launch → Retry with different browser (chromium → firefox → webkit)
  - If timeout → Increase timeout and retry
Success Criteria: Browser window visible
```

#### Step 1.2: Navigate to Reddit Homepage
```yaml
Action: Navigate to https://www.reddit.com
Wait Strategy: Wait for 'networkidle' OR specific element '.header'
Screenshot: save as 'step1_homepage.png'
Error Handling:
  - If timeout (30s) → Try https://old.reddit.com instead
  - If js_challenge detected → Wait 10s, take screenshot, check for CAPTCHA
  - If CAPTCHA detected → Pause and notify user to solve manually
Success Criteria: Reddit homepage loads with logo visible
```

#### Step 1.3: Check Authentication Status
```yaml
Action: Check if user is logged in
Detection Methods:
  1. Look for username element in header
  2. Check for "login" button (means not logged in)
  3. Check cookies for reddit_session
Screenshot: save as 'step1_auth_status.png'
Branching Logic:
  - IF logged in → Proceed to Phase 2
  - IF not logged in → Execute Phase 1.4
```

#### Step 1.4: Handle Login Requirement (If Needed)
```yaml
Action: Navigate to login page and wait for manual login
Steps:
  1. Navigate to https://www.reddit.com/login
  2. Take screenshot 'step1_login_page.png'
  3. Display message: "Please log in to Reddit in the browser window"
  4. Wait for login completion by polling for username element
  5. Max wait: 300s (5 minutes)
  6. Take screenshot every 30s to track progress
Error Handling:
  - If timeout waiting for login → Ask user if they completed login
  - If login fails → Capture error message, save screenshot, exit with clear error
Success Criteria: Username visible in header OR reddit_session cookie present
```

### Phase 2: Navigate to Apps Page
**Goal:** Successfully load the Reddit apps management page

#### Step 2.1: Navigate to Preferences
```yaml
Action: Navigate to https://www.reddit.com/prefs
Wait Strategy: Wait for preferences page to load
Screenshot: save as 'step2_prefs.png'
Error Handling:
  - If 404 → Try old.reddit.com/prefs
  - If redirected → Follow redirect and note new URL
  - If js_challenge → Wait 15s, retry once
Success Criteria: Preferences page loads with navigation visible
```

#### Step 2.2: Navigate to Apps Section
```yaml
Action: Navigate to https://www.reddit.com/prefs/apps
Wait Strategy:
  - Primary: Wait for '#developed-apps' element
  - Fallback: Wait for '.create-app-button' element
  - Timeout: 30s
Screenshot: save as 'step2_apps_page.png'
Error Handling:
  - If js_challenge=1 in URL → Detected as bot:
    * Take screenshot 'step2_bot_detected.png'
    * Wait 20s for challenge to resolve
    * Retry navigation
    * If still fails → Try old.reddit.com/prefs/apps
  - If timeout → Refresh page once, then retry
  - If 403/404 → Capture error, try alternative URLs
Success Criteria: Apps page loaded OR error message visible
```

### Phase 3: Error Message Detection & Handling
**Goal:** Identify if there are any blocking errors

#### Step 3.1: Check for App Limit Error
```yaml
Action: Scan page for error messages
Search Patterns:
  - "cannot create any more applications"
  - "developer on 0 or more applications"
  - "reach out to us"
Screenshot: save as 'step3_error_check.png'
Branching Logic:
  - IF error found → Execute Phase 3.2 (Check Existing Apps)
  - IF no error → Execute Phase 3.3 (Check for Create Button)
```

#### Step 3.2: Extract Existing Apps (Error Case)
```yaml
Action: Look for existing app listings
Selectors to Try:
  1. '.developed-app'
  2. '[data-test-id="app-card"]'
  3. '.app-box'
  4. Any div containing "client id" text
Screenshot: save as 'step3_existing_apps.png'
Error Handling:
  - If no apps found → Save error state, note user needs to contact Reddit
  - If apps found → Proceed to Phase 4
Success Criteria: List of existing apps identified
```

#### Step 3.3: Check Create Button Availability
```yaml
Action: Look for "create app" or "create another app" button
Selectors:
  1. 'button:has-text("create app")'
  2. 'button:has-text("create another app")'
  3. '.create-app-button'
Screenshot: save as 'step3_create_check.png'
Branching Logic:
  - IF button found → User can create new app (Phase 5 available)
  - IF no button found → Check for existing apps (Phase 4)
```

### Phase 4: Extract Existing App Credentials
**Goal:** Extract Client ID and Client Secret from existing apps

#### Step 4.1: Identify All Apps
```yaml
Action: Find all app containers on page
Method:
  1. Query all elements matching app selectors
  2. For each element, extract:
     - App name (h3, .app-name, etc.)
     - Container reference for further extraction
Screenshot: save as 'step4_app_list.png'
Data Structure:
  apps: [
    {name: "app1", element_id: "..."},
    {name: "app2", element_id: "..."}
  ]
Error Handling:
  - If no apps found → Search for any text containing pattern [a-zA-Z0-9]{14}
  - If still none → Save page HTML to 'step4_page_dump.html' for analysis
Success Criteria: At least one app identified
```

#### Step 4.2: Extract Client IDs
```yaml
Action: For each app, extract the Client ID
Extraction Strategy:
  1. Look for text under app name
  2. Pattern match: [a-zA-Z0-9_-]{14}
  3. Common locations:
     - Direct text under app heading
     - Element with class 'client-id'
     - Code/pre tag with monospace text
Screenshot: save as 'step4_client_ids.png'
Validation:
  - Verify length is ~14 characters
  - Verify contains alphanumeric characters
  - Verify pattern matches Reddit client ID format
Error Handling:
  - If extraction fails → Try OCR on screenshot
  - If multiple IDs found → Save all, let user choose
Success Criteria: At least one valid Client ID extracted
```

#### Step 4.3: Extract/Generate Client Secret
```yaml
Action: Get the Client Secret for each app
Sub-Steps:
  1. Look for "secret" button/link for each app
  2. Click "edit" or "secret" button
  3. Wait for secret to appear (could be in modal or inline)
  4. Extract secret text (pattern: [a-zA-Z0-9_-]{20,30})
  5. Take screenshot after each extraction
Screenshot Pattern: 'step4_secret_{app_name}.png'
Error Handling:
  - If no secret button → Note that secret may be hidden
  - If click fails → Try alternative selectors
  - If secret not visible → Click "regenerate secret" if available
  - If regenerate needed → WARN USER that old secret will be invalidated
Alternative Strategy:
  - If secrets cannot be extracted, note in output:
    "Client secrets are hidden. User must click 'edit' and view manually"
Success Criteria: Client secret extracted OR noted as requiring manual action
```

### Phase 5: Create New App (If Available)
**Goal:** If user can create new apps, automate the creation process

#### Step 5.1: Click Create App Button
```yaml
Action: Click the create app button
Wait: For form to appear
Screenshot: save as 'step5_create_form.png'
Error Handling:
  - If button not clickable → Scroll into view, retry
  - If form doesn't appear → Check for modal, popup
  - If error message appears → Capture and save
Success Criteria: App creation form visible
```

#### Step 5.2: Fill App Creation Form
```yaml
Action: Fill in required fields
Fields:
  - name: "ai-assistant-bot-{timestamp}" (avoid "reddit")
  - type: "script" (select radio button)
  - description: "Personal AI assistant" (optional)
  - about_url: "" (leave blank)
  - redirect_uri: "http://localhost:8080"
Validation Before Submit:
  - Verify name doesn't contain "reddit"
  - Verify all required fields filled
  - Screenshot: 'step5_filled_form.png'
Error Handling:
  - If field not fillable → Try alternative selectors
  - If validation error → Capture message, adjust values
Success Criteria: Form completely filled
```

#### Step 5.3: Submit Form
```yaml
Action: Click create/submit button
Wait: For app to be created and page to update
Screenshot: save as 'step5_created_app.png'
Error Handling:
  - If error message appears → Capture exact text, save to output
  - If timeout → Check if app appears in list anyway
  - If duplicate name → Retry with different timestamp
Success Criteria: New app appears in apps list
```

#### Step 5.4: Extract New App Credentials
```yaml
Action: Extract Client ID and Secret from newly created app
Process: Same as Phase 4.2 and 4.3
Focus: On the most recently created app
Screenshot: save as 'step5_new_credentials.png'
Success Criteria: Both Client ID and Secret extracted
```

### Phase 6: Save Credentials
**Goal:** Save all extracted data to JSON file (NOT .env)

#### Step 6.1: Structure Credential Data
```yaml
Action: Organize all extracted information
Data Structure:
{
  "extraction_timestamp": "2024-01-...",
  "reddit_apps_url": "actual URL visited",
  "extraction_status": "success/partial/failed",
  "apps": [
    {
      "app_name": "...",
      "client_id": "...",
      "client_secret": "..." OR "MANUAL_EXTRACTION_REQUIRED",
      "notes": "any special notes"
    }
  ],
  "errors": [],
  "screenshots": [list of screenshot files],
  "next_steps": "instructions for user"
}
```

#### Step 6.2: Write to File
```yaml
Action: Save to reddit_credentials.json
Location: /Users/home/aimacpro/reddit-ai-assistant/reddit_credentials.json
Format: Pretty-printed JSON with 2-space indentation
Backup: If file exists, rename to reddit_credentials.backup.json
Error Handling:
  - If write fails → Try alternative location
  - If permissions issue → Save to /tmp/ and notify user
Success Criteria: File created with valid JSON
```

#### Step 6.3: Final Screenshot & Summary
```yaml
Action: Take final screenshot and generate summary
Screenshot: 'step6_final_state.png'
Summary Output:
  - Total apps found: N
  - Client IDs extracted: N
  - Client Secrets extracted: N
  - Manual actions required: [list]
  - File saved to: [path]
```

### Phase 7: Cleanup & Error Reporting
**Goal:** Close browser and report results

#### Step 7.1: Generate Detailed Report
```yaml
Action: Create human-readable report
File: reddit_extraction_report.txt
Contents:
  - Timestamp
  - Success/failure status
  - All screenshots taken (with descriptions)
  - Credentials found (Client IDs only, secrets marked as present/absent)
  - Any errors encountered
  - Next steps for user
```

#### Step 7.2: Close Browser
```yaml
Action: Gracefully close Playwright browser
Wait: 2s to ensure all screenshots saved
Error Handling:
  - Ensure cleanup even if earlier steps failed
```

## COMPREHENSIVE ERROR HANDLING MATRIX

### Bot Detection Errors
```yaml
Error: js_challenge=1 in URL
Response:
  1. Take screenshot 'error_bot_challenge.png'
  2. Wait 20 seconds
  3. Retry navigation
  4. If fails again → Try old.reddit.com
  5. If still fails → Save state and report to user
```

### Timeout Errors
```yaml
Error: Page load timeout
Response:
  1. Take screenshot 'error_timeout.png'
  2. Check current URL
  3. Check network state
  4. Retry once with extended timeout
  5. If fails → Try alternative URL
```

### Element Not Found Errors
```yaml
Error: Cannot find expected element
Response:
  1. Take screenshot 'error_element_missing.png'
  2. Save page HTML to 'error_page_dump.html'
  3. Try alternative selectors from backup list
  4. If still fails → Note in report, continue with other steps
```

### Authentication Errors
```yaml
Error: Not logged in / session expired
Response:
  1. Take screenshot 'error_not_logged_in.png'
  2. Navigate to login page
  3. Wait for user to log in (with timeout)
  4. Verify login success
  5. Retry from current phase
```

### Permission Errors
```yaml
Error: Access denied / 403
Response:
  1. Take screenshot 'error_permission.png'
  2. Check if logged in
  3. Check if correct user permissions
  4. Report to user with specific error
```

## EXECUTION PSEUDOCODE

```python
def execute_reddit_credential_extraction():
    # Phase 1: Setup
    browser = launch_browser_with_persistence()
    screenshots = []
    errors = []
    apps_data = []

    try:
        # Phase 1.2: Navigate to Reddit
        navigate_to_reddit_homepage(browser, screenshots, errors)

        # Phase 1.3: Check auth
        is_logged_in = check_authentication_status(browser, screenshots)

        # Phase 1.4: Login if needed
        if not is_logged_in:
            wait_for_manual_login(browser, screenshots, timeout=300)

        # Phase 2: Navigate to apps
        navigate_to_apps_page(browser, screenshots, errors)

        # Phase 3: Error detection
        has_error = check_for_app_limit_error(browser, screenshots)

        # Phase 4: Extract existing apps
        apps_data = extract_existing_apps(browser, screenshots, errors)

        # Phase 5: Create new app if possible
        if can_create_new_app(browser):
            new_app = create_new_app(browser, screenshots, errors)
            if new_app:
                apps_data.append(new_app)

        # Phase 6: Save credentials
        save_credentials_to_json(apps_data, screenshots, errors)

    except Exception as e:
        handle_critical_error(e, screenshots, errors)

    finally:
        # Phase 7: Cleanup
        generate_report(apps_data, screenshots, errors)
        close_browser(browser)

    return apps_data
```

## SUCCESS CRITERIA

### Minimum Success
- ✓ At least 1 Client ID extracted
- ✓ Credentials saved to reddit_credentials.json
- ✓ Screenshots captured at each step
- ✓ Clear report of what was found

### Full Success
- ✓ All existing apps identified
- ✓ Client IDs and Secrets extracted
- ✓ No errors during extraction
- ✓ Complete credentials ready to use

### Partial Success
- ✓ Client IDs found but secrets need manual extraction
- ✓ Detailed instructions provided for manual steps
- ✓ Screenshots show exactly where to find missing data

## OUTPUT FILES

```
/Users/home/aimacpro/reddit-ai-assistant/
├── reddit_credentials.json          # Main output
├── reddit_extraction_report.txt     # Human-readable report
└── screenshots/
    ├── step1_homepage.png
    ├── step1_auth_status.png
    ├── step2_apps_page.png
    ├── step3_error_check.png
    ├── step4_client_ids.png
    ├── step5_created_app.png
    ├── step6_final_state.png
    └── error_*.png (if any)
```

## ESTIMATED EXECUTION TIME
- Best case (already logged in, apps exist): 30-45 seconds
- Typical case (need to handle some errors): 60-90 seconds
- Worst case (manual login required): 5-10 minutes

This plan handles EVERY possible scenario with Reddit's apps page while avoiding touching the .env file.
