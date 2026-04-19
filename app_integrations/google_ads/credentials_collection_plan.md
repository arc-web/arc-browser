# Google Ads Credentials Collection - Execution Plan

## Quick Start

This plan provides step-by-step instructions for collecting Google Ads API credentials using browser automation or manual steps.

---

## Prerequisites

- Google account with access to:
  - Google Cloud Console
  - Google Ads MCC account (211-993-1898)
- Browser automation tool (Playwright MCP or browser automation agent)

---

## Execution Options

### Option 1: Browser Automation (Recommended)
Use Playwright MCP or browser automation agent to automate credential collection.

**See**: `browser_automation_plan.md` for detailed automation scripts

### Option 2: Manual Steps
Follow manual instructions if automation encounters issues.

**See**: `GET_CREDENTIALS_GUIDE.md` for manual step-by-step guide

---

## Credentials Checklist

- [ ] **Client ID** - From Google Cloud Console
- [ ] **Client Secret** - From Google Cloud Console  
- [ ] **Developer Token** - From Google Ads API Center
- [ ] **Refresh Token** - From OAuth Playground
- [ ] **MCC ID** - Already configured: 2119931898 ✅

---

## Quick Reference URLs

| Purpose | URL |
|---------|-----|
| Google Cloud Console | https://console.cloud.google.com |
| Google Ads | https://ads.google.com |
| API Center (Direct) | https://ads.google.com/aw/apicenter |
| OAuth Playground | https://developers.google.com/oauthplayground |

---

## Step-by-Step Summary

### 1. Google Cloud Console (5-10 minutes)
- Enable Google Ads API
- Create OAuth 2.0 Desktop app credentials
- Copy Client ID and Client Secret

### 2. Google Ads (2-5 minutes)
- Navigate to API Center
- Copy Developer Token (or apply if needed)

### 3. OAuth Playground (3-5 minutes)
- Configure with Client ID/Secret
- Authorize Google Ads API scope
- Exchange for Refresh Token

### 4. Update Config (1 minute)
- Edit `google-ads.yaml`
- Paste all credentials
- Save file

### 5. Verify (2 minutes)
- Run `python3 test_server.py`
- Check MCP connection

**Total Time**: ~15-25 minutes

---

## Using Browser Automation

### With Playwright MCP

```bash
# Navigate to Google Cloud Console
# Use MCP tool: navigate
# URL: https://console.cloud.google.com

# Follow steps in browser_automation_plan.md
```

### With Browser Automation Agent

```typescript
// Use BrowserAutomationAgent
const agent = new BrowserAutomationAgent();
await agent.executeTask({
  type: 'navigate',
  url: 'https://console.cloud.google.com',
  // ... follow automation plan
});
```

---

## Manual Collection Steps

If automation isn't working, follow these manual steps:

### Step 1: Client ID & Secret
1. Go to https://console.cloud.google.com
2. Select project
3. APIs & Services → Library
4. Search "Google Ads API" → Enable
5. APIs & Services → Credentials
6. Create Credentials → OAuth client ID
7. Application type: Desktop app
8. Copy Client ID and Client Secret

### Step 2: Developer Token
1. Go to https://ads.google.com
2. Tools → API Center
3. Copy Developer Token

### Step 3: Refresh Token
1. Go to https://developers.google.com/oauthplayground
2. Settings → Use your own OAuth credentials
3. Enter Client ID and Secret
4. Find "Google Ads API" → Select scope
5. Authorize → Allow
6. Exchange authorization code → Copy Refresh Token

### Step 4: Update Config
Edit `/Users/home/aimacpro/7_tools/mcp_tools/servers/google_ads_mcp/google-ads.yaml`:

```yaml
client_id: <your-client-id>
client_secret: <your-client-secret>
refresh_token: <your-refresh-token>
developer_token: <your-developer-token>
login_customer_id: 2119931898
```

---

## Verification

After collecting credentials:

```bash
cd /Users/home/aimacpro/7_tools/mcp_tools/servers/google_ads_mcp

# Test server
python3 test_server.py

# Check MCP connection
claude mcp list

# Should show: google-ads: ✓ Connected
```

---

## Troubleshooting

### "Invalid credentials"
- Check for extra spaces/newlines
- Verify all values copied correctly
- Ensure Client ID/Secret match

### "Developer token not approved"
- Check API Center for approval status
- May need to wait 24-48 hours
- Use test account if available

### "Refresh token expired"
- Re-generate via OAuth Playground
- Ensure using correct Client ID/Secret

### Browser automation fails
- Switch to manual steps
- Check selectors in browser_automation_plan.md
- May need to handle 2FA/captcha manually

---

## Security Reminders

⚠️ **Never commit credentials to git**
- Keep `google-ads.yaml` in `.gitignore`
- Use environment variables for production
- Rotate credentials periodically

---

## Next Steps After Collection

1. ✅ Run test suite: `bash test_mcc_integration.sh`
2. ✅ Test MCP connection
3. ✅ Verify MCC account access
4. ✅ Test apps with real data
5. ✅ Execute workflows

See `TESTING_GUIDE.md` for detailed testing instructions.

---

## Support

If you encounter issues:
1. Review `GET_CREDENTIALS_GUIDE.md` for detailed steps
2. Check `browser_automation_plan.md` for automation help
3. Verify MCC account has API access enabled
4. Ensure developer token has proper permissions

