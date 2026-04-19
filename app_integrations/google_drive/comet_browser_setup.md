# Comet Browser Setup Guide

## Deep Link to Google Cloud Console

Click this link to open Google Cloud Console in Comet browser:

**https://console.cloud.google.com/apis/library/drive.googleapis.com**

Or use this direct link to the credentials page:
**https://console.cloud.google.com/apis/credentials**

---

## Prompt for Comet Browser

Copy and paste this prompt into Comet browser to automate the Google Drive OAuth setup:

```
I need to set up Google Drive API OAuth credentials for an MCP server. Please help me:

1. Navigate to Google Cloud Console: https://console.cloud.google.com/
2. If no project is selected, create a new project called "Google Drive MCP" or select an existing project
3. Enable Google Drive API:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click on it and press "Enable"
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - If prompted, configure the OAuth consent screen first:
     * User Type: External (unless you have a Google Workspace)
     * App name: "Google Drive MCP Server"
     * User support email: [your email]
     * Developer contact: [your email]
     * Click "Save and Continue" through the scopes (no need to add scopes here)
     * Click "Save and Continue" through test users (skip if not needed)
     * Click "Back to Dashboard"
   - Now create OAuth client ID:
     * Application type: "Desktop app"
     * Name: "Google Drive MCP Desktop Client"
     * Click "Create"
5. Download the credentials:
   - Click the download button (arrow icon) next to the newly created OAuth client
   - Save the file as "credentials.json"
   - Make sure it's saved to: /Users/home/aimacmini/google-drive-assistant/mcp-server/credentials.json

Once the credentials.json file is downloaded, let me know and I'll help you complete the OAuth authentication flow.
```

---

## Alternative: Step-by-Step Manual Instructions

If you prefer to do it manually, here are the steps:

### Step 1: Open Google Cloud Console
**Deep Link**: https://console.cloud.google.com/

### Step 2: Enable Google Drive API
**Deep Link**: https://console.cloud.google.com/apis/library/drive.googleapis.com
- Click "Enable" button

### Step 3: Configure OAuth Consent Screen (if needed)
**Deep Link**: https://console.cloud.google.com/apis/credentials/consent
- User Type: External
- App name: "Google Drive MCP Server"
- Fill in required fields
- Save and Continue

### Step 4: Create OAuth 2.0 Client ID
**Deep Link**: https://console.cloud.google.com/apis/credentials
- Click "Create Credentials" → "OAuth client ID"
- Application type: **Desktop app**
- Name: "Google Drive MCP Desktop Client"
- Click "Create"
- Click download button to save `credentials.json`

### Step 5: Save credentials.json
Save the downloaded file to:
```
/Users/home/aimacmini/google-drive-assistant/mcp-server/credentials.json
```

---

## After Downloading credentials.json

Once you have `credentials.json` saved, run this command in your terminal:

```bash
cd /Users/home/aimacmini/google-drive-assistant/mcp-server
python3 src/auth_setup.py --credentials credentials.json
```

This will:
- Open a browser window for OAuth authentication
- Request Google Drive permissions
- Save the token to `credentials/token.pickle`
- Complete the setup!

---

## Quick Links Reference

- **Google Cloud Console**: https://console.cloud.google.com/
- **Google Drive API Library**: https://console.cloud.google.com/apis/library/drive.googleapis.com
- **Credentials Page**: https://console.cloud.google.com/apis/credentials
- **OAuth Consent Screen**: https://console.cloud.google.com/apis/credentials/consent

