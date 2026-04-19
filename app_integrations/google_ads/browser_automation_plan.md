# Browser Automation Plan for Google Ads Credentials

## Overview

This document provides a detailed browser automation plan to collect Google Ads API credentials using Playwright or browser automation tools.

---

## Automation Strategy

### Tools Available
- **Browser Automation Agent**: `/Users/home/aimacpro/4_agents/browser_automation_agent/`
  - **Playwright MCP**: `4_agents/browser_automation_agent/playwright/mcp/`
  
**Note**: Apps should call the browser agent to execute this plan, rather than running browser automation directly.

### Approach
1. Use browser automation to navigate through credential collection steps
2. Extract values from pages
3. Update configuration file automatically
4. Verify credentials work

---

## Part 1: Google Cloud Console - Client ID & Secret

### Automation Steps

```javascript
// Step 1: Navigate to Google Cloud Console
await page.goto('https://console.cloud.google.com');
await page.waitForLoadState('networkidle');

// Step 2: Select/Create Project (may need user interaction)
// Look for project selector
const projectSelector = await page.locator('[aria-label*="Select a project"]').first();
if (await projectSelector.isVisible()) {
  await projectSelector.click();
  // User may need to select project manually
  await page.waitForTimeout(2000);
}

// Step 3: Navigate to APIs & Services
await page.click('text="APIs & Services"');
await page.waitForLoadState('networkidle');

// Step 4: Go to Library
await page.click('text="Library"');
await page.waitForLoadState('networkidle');

// Step 5: Search for Google Ads API
await page.fill('input[placeholder*="Search"]', 'Google Ads API');
await page.waitForTimeout(1000);

// Step 6: Click on Google Ads API result
await page.click('text="Google Ads API"');
await page.waitForLoadState('networkidle');

// Step 7: Enable API
const enableButton = page.locator('button:has-text("Enable")');
if (await enableButton.isVisible()) {
  await enableButton.click();
  await page.waitForLoadState('networkidle');
}

// Step 8: Navigate to Credentials
await page.click('text="Credentials"');
await page.waitForLoadState('networkidle');

// Step 9: Create OAuth Credentials
await page.click('button:has-text("CREATE CREDENTIALS")');
await page.waitForTimeout(1000);
await page.click('text="OAuth client ID"');

// Step 10: Configure OAuth Consent Screen (if needed)
// Check if consent screen needs configuration
const configureConsent = page.locator('text="Configure Consent Screen"');
if (await configureConsent.isVisible()) {
  await configureConsent.click();
  // User Type selection
  await page.click('text="External"'); // or "Internal"
  await page.click('button:has-text("CREATE")');
  
  // Fill consent screen form
  await page.fill('input[name="appName"]', 'Google Ads MCP');
  await page.fill('input[type="email"]', 'your-email@example.com');
  await page.click('button:has-text("Save and Continue")');
  
  // Add scopes
  await page.click('button:has-text("ADD OR REMOVE SCOPES")');
  await page.fill('input[placeholder*="Filter"]', 'adwords');
  await page.check('input[value*="adwords"]');
  await page.click('button:has-text("UPDATE")');
  await page.click('button:has-text("Save and Continue")');
  
  // Add test users
  await page.fill('input[placeholder*="email"]', 'your-email@example.com');
  await page.click('button:has-text("ADD USERS")');
  await page.click('button:has-text("Save and Continue")');
  
  // Back to credentials
  await page.click('text="Credentials"');
}

// Step 11: Create OAuth Client
await page.selectOption('select', 'Desktop app');
await page.fill('input[name="name"]', 'Google Ads MCP Desktop Client');
await page.click('button:has-text("Create")');

// Step 12: Extract Credentials
await page.waitForSelector('text="Your Client ID"', { timeout: 10000 });
const clientId = await page.locator('input[value*="apps.googleusercontent.com"]').inputValue();
const clientSecret = await page.locator('input[type="password"]').inputValue();

// Or extract from text if not in inputs
// const clientIdText = await page.locator('text=/[0-9]+-[a-zA-Z0-9]+\.apps\.googleusercontent\.com/').textContent();
// const clientSecretText = await page.locator('text=/[a-zA-Z0-9]{24,}/').textContent();

console.log('Client ID:', clientId);
console.log('Client Secret:', clientSecret);
```

### Key Selectors

| Element | Selector |
|---------|----------|
| Project Selector | `[aria-label*="Select a project"]` |
| APIs & Services | `text="APIs & Services"` |
| Library | `text="Library"` |
| Search Box | `input[placeholder*="Search"]` |
| Google Ads API | `text="Google Ads API"` |
| Enable Button | `button:has-text("Enable")` |
| Credentials | `text="Credentials"` |
| Create Credentials | `button:has-text("CREATE CREDENTIALS")` |
| OAuth Client ID | `text="OAuth client ID"` |
| Desktop App | `text="Desktop app"` |
| Client ID Value | `input[value*="apps.googleusercontent.com"]` |
| Client Secret Value | `input[type="password"]` |

---

## Part 2: Google Ads - Developer Token

### Automation Steps

```javascript
// Step 1: Navigate to Google Ads
await page.goto('https://ads.google.com');
await page.waitForLoadState('networkidle');

// Step 2: Handle account selection if needed
const accountSelector = page.locator('text=/211-993-1898/');
if (await accountSelector.isVisible()) {
  await accountSelector.click();
  await page.waitForLoadState('networkidle');
}

// Step 3: Click Tools icon
await page.click('button[aria-label*="Tools"]');
await page.waitForTimeout(1000);

// Step 4: Navigate to API Center
// Option 1: Click API Center link
await page.click('text="API Center"');
// Option 2: Direct URL
// await page.goto('https://ads.google.com/aw/apicenter');

await page.waitForLoadState('networkidle');

// Step 5: Find Developer Token section
const devTokenSection = page.locator('text="Developer Token"');
await devTokenSection.waitFor({ timeout: 10000 });

// Step 6: Extract Developer Token
// Look for copy button or token display
const copyButton = page.locator('button[aria-label*="Copy"]').first();
if (await copyButton.isVisible()) {
  await copyButton.click();
  // Token is now in clipboard, need to read it
  const developerToken = await page.evaluate(() => navigator.clipboard.readText());
} else {
  // Try to find token in text
  const tokenElement = page.locator('text=/[A-Za-z0-9]{10,}/').first();
  const developerToken = await tokenElement.textContent();
}

console.log('Developer Token:', developerToken);
```

### Key Selectors

| Element | Selector |
|---------|----------|
| Tools Icon | `button[aria-label*="Tools"]` |
| API Center | `text="API Center"` |
| Developer Token Section | `text="Developer Token"` |
| Copy Button | `button[aria-label*="Copy"]` |
| Token Text | `text=/[A-Za-z0-9]{10,}/` |

---

## Part 3: OAuth Playground - Refresh Token

### Automation Steps

```javascript
// Step 1: Navigate to OAuth Playground
await page.goto('https://developers.google.com/oauthplayground');
await page.waitForLoadState('networkidle');

// Step 2: Open Settings
await page.click('button[aria-label*="Settings"]');
await page.waitForTimeout(1000);

// Step 3: Enable "Use your own OAuth credentials"
const checkbox = page.locator('input[type="checkbox"]').first();
await checkbox.check();

// Step 4: Enter Client ID
await page.fill('input[name*="client_id"]', clientId); // From Part 1

// Step 5: Enter Client Secret
await page.fill('input[name*="client_secret"]', clientSecret); // From Part 1

// Step 6: Close Settings
await page.click('button:has-text("Close")');
await page.waitForTimeout(1000);

// Step 7: Find Google Ads API scope
await page.fill('input[placeholder*="Search"]', 'Google Ads API');
await page.waitForTimeout(1000);

// Step 8: Select scope
await page.check('input[value*="adwords"]');

// Step 9: Authorize
await page.click('button:has-text("Authorize APIs")');
await page.waitForLoadState('networkidle');

// Step 10: Handle Google Sign-in (may need user interaction)
// Wait for redirect to Google sign-in
await page.waitForURL('**/accounts.google.com/**', { timeout: 30000 });

// User may need to sign in manually
// Wait for redirect back to playground
await page.waitForURL('**/oauthplayground**', { timeout: 60000 });

// Step 11: Exchange for tokens
await page.click('button:has-text("Exchange authorization code for tokens")');
await page.waitForLoadState('networkidle');

// Step 12: Extract Refresh Token
const refreshTokenElement = page.locator('textarea, input').filter({ hasText: /^1\/\/[A-Za-z0-9_-]+$/ });
const refreshToken = await refreshTokenElement.inputValue();

// Or find by label
const refreshTokenLabel = page.locator('text="Refresh token"');
const refreshTokenField = refreshTokenLabel.locator('..').locator('textarea, input').first();
const refreshToken = await refreshTokenField.inputValue();

console.log('Refresh Token:', refreshToken);
```

### Key Selectors

| Element | Selector |
|---------|----------|
| Settings Button | `button[aria-label*="Settings"]` |
| Use Own Credentials Checkbox | `input[type="checkbox"]` |
| Client ID Input | `input[name*="client_id"]` |
| Client Secret Input | `input[name*="client_secret"]` |
| Google Ads Scope | `input[value*="adwords"]` |
| Authorize Button | `button:has-text("Authorize APIs")` |
| Exchange Button | `button:has-text("Exchange")` |
| Refresh Token Field | `textarea` or `input` near "Refresh token" label |

---

## Part 4: Update Configuration File

### Automation Steps

```javascript
const fs = require('fs');
const path = require('path');

// Read current config
const configPath = '/Users/home/aimacpro/7_tools/mcp_tools/servers/google_ads_mcp/google-ads.yaml';
const configContent = fs.readFileSync(configPath, 'utf8');

// Replace placeholders
const updatedConfig = configContent
  .replace('YOUR_CLIENT_ID_HERE', clientId)
  .replace('YOUR_CLIENT_SECRET_HERE', clientSecret)
  .replace('YOUR_REFRESH_TOKEN_HERE', refreshToken)
  .replace('YOUR_DEVELOPER_TOKEN_HERE', developerToken)
  .replace('YOUR_LOGIN_CUSTOMER_ID_HERE', '2119931898');

// Write updated config
fs.writeFileSync(configPath, updatedConfig, 'utf8');

console.log('Configuration file updated successfully!');
```

---

## Complete Automation Script Structure

```javascript
const { chromium } = require('playwright');
const fs = require('fs');

async function collectGoogleAdsCredentials() {
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  let clientId, clientSecret, developerToken, refreshToken;

  try {
    // Part 1: Get Client ID & Secret
    console.log('Step 1: Getting Client ID and Secret...');
    ({ clientId, clientSecret } = await getOAuthCredentials(page));
    
    // Part 2: Get Developer Token
    console.log('Step 2: Getting Developer Token...');
    developerToken = await getDeveloperToken(page);
    
    // Part 3: Get Refresh Token
    console.log('Step 3: Getting Refresh Token...');
    refreshToken = await getRefreshToken(page, clientId, clientSecret);
    
    // Part 4: Update Config
    console.log('Step 4: Updating configuration file...');
    updateConfigFile(clientId, clientSecret, developerToken, refreshToken);
    
    console.log('✅ All credentials collected and saved!');
    
  } catch (error) {
    console.error('❌ Error:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

// Implement helper functions:
// - getOAuthCredentials(page)
// - getDeveloperToken(page)
// - getRefreshToken(page, clientId, clientSecret)
// - updateConfigFile(...)

collectGoogleAdsCredentials();
```

---

## Using Playwright MCP

If using Playwright MCP, you can call these steps via MCP tools:

```json
{
  "tool": "navigate",
  "arguments": {
    "url": "https://console.cloud.google.com"
  }
}
```

```json
{
  "tool": "click",
  "arguments": {
    "selector": "text=\"APIs & Services\""
  }
}
```

```json
{
  "tool": "extract_text",
  "arguments": {
    "selector": "input[value*=\"apps.googleusercontent.com\"]"
  }
}
```

---

## Manual Intervention Points

Some steps may require manual intervention:

1. **Google Sign-in**: May require 2FA or captcha
2. **Project Selection**: User may need to select project
3. **OAuth Consent**: May need to configure consent screen
4. **Authorization**: User needs to approve permissions
5. **Developer Token Approval**: May need to wait for approval

---

## Error Handling

```javascript
// Handle common errors
try {
  await page.click('selector');
} catch (error) {
  if (error.message.includes('not found')) {
    // Try alternative selector
    await page.click('alternative-selector');
  } else if (error.message.includes('timeout')) {
    // Wait longer or check if page loaded
    await page.waitForLoadState('networkidle');
  }
}
```

---

## Next Steps

1. Implement browser automation script
2. Test each part individually
3. Handle edge cases and errors
4. Add verification steps
5. Create automated test after credential collection

