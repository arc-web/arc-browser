# Browser Agent Setup Guide

Complete guide for setting up the browser agent with all necessary logins and browser extensions.

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [Extension Support](#extension-support)
3. [1Password Integration](#1password-integration)
4. [Manual Login Setup](#manual-login-setup)
5. [Configuration](#configuration)
6. [Troubleshooting](#troubleshooting)

---

## Initial Setup

### 1. Install Dependencies

```bash
cd 4_agents/browser_automation_agent
./setup.sh
```

### 2. Build the Project

```bash
cd playwright/mcp
npm run build
```

---

## Extension Support

The browser agent **fully supports browser extensions**, including:
- ✅ 1Password (password manager)
- ✅ Ad blockers
- ✅ Developer tools
- ✅ Any Chrome/Chromium extension

### Automated Extension Installation

The browser agent can **automatically install extensions** from Chrome Web Store! Use the `browser_install_extension` tool:

```javascript
browser_install_extension({
  webStoreUrl: "https://chrome.google.com/webstore/detail/extension-id"
})
```

This will:
- Navigate to the extensions page
- Enable Developer Mode
- Navigate to the Chrome Web Store
- Click "Add to Chrome"
- Handle confirmation dialogs

**No manual steps required!**

### How Extensions Work

The browser agent uses Playwright's `launchPersistentContext()` when a `userDataDir` is configured. This creates a persistent browser profile where:

1. **Extensions can be installed** - Just like a regular Chrome browser
2. **Extension settings persist** - Your extension configurations are saved
3. **Login sessions persist** - Cookies and auth tokens are maintained
4. **Extension data persists** - 1Password vaults, saved passwords, etc.

---

## 1Password Integration

### Option 1: Using Persistent User Data Directory (Recommended)

This method allows you to install 1Password extension directly in the browser profile, just like you would in a regular Chrome browser.

#### Step 1: Configure User Data Directory

Update your MCP configuration (`7_tools/mcp_tools/mcp_config.json`):

```json
{
  "playwright": {
    "command": "node",
    "args": ["/Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp/dist/server.js"],
    "env": {
      "BROWSER_STATE_DIR": "/Users/home/aimacpro/.browser-states",
      "BROWSER_USER_DATA_DIR": "/Users/home/aimacpro/.browser-profile",
      "HEADLESS": "false"
    }
  }
}
```

#### Step 2: Install 1Password Extension

**Option A: Automated Installation (Recommended)**

The browser agent can automatically install extensions from Chrome Web Store! Just use:

```javascript
browser_install_extension({
  webStoreUrl: "https://chrome.google.com/webstore/detail/1password-%E2%80%93-password-manager/aeblfdkhhhdcdjpifhhbdiojplfjncoa"
})
```

Or using natural language:
```
browser_execute("Install the 1Password extension from Chrome Web Store")
```

The agent will:
1. Navigate to `chrome://extensions/`
2. Enable Developer Mode automatically
3. Navigate to the Chrome Web Store extension page
4. Click "Add to Chrome" button
5. Handle the confirmation dialog

**Option B: Manual Installation**

1. **Start the browser agent** (it will create the user data directory)
2. **Open Chrome Extensions page**: `chrome://extensions/`
3. **Enable Developer Mode** (toggle in top right)
4. **Install 1Password**:
   - Go to [1Password Chrome Extension](https://chrome.google.com/webstore/detail/1password-%E2%80%93-password-manager/aeblfdkhhhdcdjpifhhbdiojplfjncoa)
   - Click "Add to Chrome"

**Option C: Load Unpacked Extension**

1. Download 1Password extension files
2. Navigate to `chrome://extensions/`
3. Enable Developer Mode
4. Click "Load unpacked" and select the extension directory

#### Step 3: Configure 1Password

1. **Sign in to 1Password** in the browser extension
2. **Unlock your vault** (this will be remembered)
3. **Enable autofill** for the sites you want to automate

#### Step 4: Test the Setup

The browser agent will now:
- ✅ Have 1Password extension available on all pages
- ✅ Auto-fill passwords when forms are detected
- ✅ Maintain your 1Password session across browser restarts
- ✅ Save new passwords to 1Password

### Option 2: Using Extension Paths (Advanced)

If you have the 1Password extension files locally, you can load them directly:

```json
{
  "playwright": {
    "command": "node",
    "args": ["/Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp/dist/server.js"],
    "env": {
      "BROWSER_STATE_DIR": "/Users/home/aimacpro/.browser-states",
      "BROWSER_USER_DATA_DIR": "/Users/home/aimacpro/.browser-profile",
      "BROWSER_EXTENSION_PATHS": "/path/to/1password-extension,/path/to/other-extension",
      "HEADLESS": "false"
    }
  }
}
```

**Note**: Extension paths must point to unpacked extension directories (containing `manifest.json`).

---

## Manual Login Setup

If you prefer to log in manually (without 1Password), follow these steps:

### Step 1: Start Browser in Non-Headless Mode

Ensure `HEADLESS` is set to `false` in your configuration:

```json
{
  "env": {
    "HEADLESS": "false"
  }
}
```

### Step 2: Navigate to Sites and Log In

1. **Start the browser agent**
2. **Use browser automation commands** to navigate to sites:
   ```javascript
   browser_navigate({ url: "https://example.com" })
   ```
3. **Manually log in** to each service:
   - Gmail
   - Google Ads
   - Google Analytics
   - Slack
   - Any other services you need
4. **The browser agent will automatically save**:
   - Cookies
   - Local storage
   - Session tokens
   - All authentication state

### Step 3: Verify Sessions Persist

After logging in, the browser agent saves state to:
```
{BROWSER_STATE_DIR}/mcp-browser-state.json
```

This file contains:
- All cookies
- Local storage data
- Session information

**Your logins will persist** across browser restarts!

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BROWSER_STATE_DIR` | Directory for storing browser state (cookies, sessions) | `./.mcp-browser-state` |
| `BROWSER_USER_DATA_DIR` | Persistent user data directory (enables extensions) | `undefined` (extensions disabled) |
| `BROWSER_EXTENSION_PATHS` | Comma-separated paths to extension directories | `undefined` |
| `HEADLESS` | Run browser in headless mode | `true` (set to `"false"` to see browser) |

### Example Configuration

```json
{
  "playwright": {
    "command": "node",
    "args": ["/Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp/dist/server.js"],
    "env": {
      "BROWSER_STATE_DIR": "/Users/home/aimacpro/.browser-states",
      "BROWSER_USER_DATA_DIR": "/Users/home/aimacpro/.browser-profile",
      "BROWSER_EXTENSION_PATHS": "/Users/home/.1password-extension",
      "HEADLESS": "false"
    }
  }
}
```

### When to Use Each Option

**Use `BROWSER_USER_DATA_DIR` when:**
- ✅ You want to install extensions via Chrome Web Store
- ✅ You want extensions to persist across sessions
- ✅ You want a full browser profile experience

**Use `BROWSER_EXTENSION_PATHS` when:**
- ✅ You have unpacked extension files locally
- ✅ You want to load specific extensions programmatically
- ✅ You're developing custom extensions

**Use manual login when:**
- ✅ You don't need password managers
- ✅ You prefer to log in once and let sessions persist
- ✅ You want the simplest setup

---

## Troubleshooting

### Extensions Not Loading

**Problem**: Extensions don't appear in the browser

**Solutions**:
1. Ensure `BROWSER_USER_DATA_DIR` is set
2. Check that the directory exists and is writable
3. Restart the browser agent after installing extensions
4. Verify extensions are enabled in `chrome://extensions/`

### 1Password Not Auto-Filling

**Problem**: 1Password extension is installed but not filling passwords

**Solutions**:
1. **Check 1Password is unlocked**: Click the 1Password icon in the browser
2. **Enable autofill**: In 1Password settings, ensure "Autofill" is enabled
3. **Check site permissions**: Some sites may block autofill
4. **Verify form detection**: 1Password needs to detect login forms

### Sessions Not Persisting

**Problem**: Logins are lost after browser restart

**Solutions**:
1. Check `BROWSER_STATE_DIR` is set correctly
2. Verify the state file is being created: `{BROWSER_STATE_DIR}/mcp-browser-state.json`
3. Ensure the directory is writable
4. Check browser console for state save errors

### Browser Won't Start

**Problem**: Browser fails to launch

**Solutions**:
1. **Check Playwright is installed**: `npx playwright install chromium`
2. **Verify paths are correct**: All paths in config should be absolute
3. **Check permissions**: Ensure directories are readable/writable
4. **Review logs**: Check console output for specific errors

### Extension Conflicts

**Problem**: Extensions interfere with automation

**Solutions**:
1. **Disable conflicting extensions**: Some extensions may block automation
2. **Use extension whitelist**: Only load necessary extensions
3. **Test without extensions first**: Verify automation works, then add extensions

---

## Best Practices

### Security

1. **Protect your user data directory**: It contains saved passwords and sessions
   ```bash
   chmod 700 ~/.browser-profile
   ```

2. **Use environment variables**: Don't hardcode paths in config files
   ```bash
   export BROWSER_USER_DATA_DIR="$HOME/.browser-profile"
   ```

3. **Regular backups**: Backup your browser state directory
   ```bash
   tar -czf browser-state-backup.tar.gz ~/.browser-states
   ```

### Performance

1. **Use headless mode for automation**: Set `HEADLESS=true` when you don't need to see the browser
2. **Limit extensions**: Only load extensions you actually need
3. **Clean state periodically**: Remove old state files if they get too large

### Maintenance

1. **Update extensions regularly**: Keep 1Password and other extensions updated
2. **Monitor state file size**: Large state files can slow down initialization
3. **Test after updates**: Verify automation still works after Playwright updates

---

## Next Steps

After setup:
1. ✅ Test browser automation with a simple task
2. ✅ Verify 1Password autofill works
3. ✅ Confirm sessions persist across restarts
4. ✅ Set up automation for your specific use cases

See [QUICK_START.md](./QUICK_START_BROWSER_AUTOMATION.md) for usage examples.

