# Google Ads MCP - Browser Automation for Credentials

## 🚀 Quick Start

### 1. Setup (One Time)
```bash
cd /Users/home/aimacpro/7_tools/mcp_tools/servers/google_ads_mcp
bash setup_automation.sh
```

### 2. Run Automation via Browser Agent

**Recommended**: Call the browser agent to execute the automation plan:
```python
from browser_automation_agent.orchestrator import BrowserAutomationOrchestrator

orchestrator = BrowserAutomationOrchestrator()
result = await orchestrator.execute_plan(
    plan_path="4_agents/browser_automation_agent/app_integrations/google_ads/browser_automation_plan.md"
)
```

**Alternative** (direct script execution):
```bash
cd /Users/home/aimacpro/7_tools/mcp_tools/servers/google_ads_mcp
python3 collect_credentials_automated.py
```

The browser agent will open a browser and guide you through collecting all credentials automatically!

---

## 📋 What You'll Collect

| Credential | Source | Status |
|------------|--------|--------|
| Client ID | Google Cloud Console | ⚠️ Need to collect |
| Client Secret | Google Cloud Console | ⚠️ Need to collect |
| Developer Token | Google Ads API Center | ⚠️ Need to collect |
| Refresh Token | OAuth Playground | ⚠️ Need to collect |
| MCC ID | Your account | ✅ Already set: 2119931898 |

---

## 🎯 How It Works

The automation script (`collect_credentials_automated.py`) uses Playwright to:

1. **Navigate** through Google Cloud Console, Google Ads, and OAuth Playground
2. **Extract** credentials automatically when possible
3. **Prompt** you for manual steps (sign-in, approvals)
4. **Update** `google-ads.yaml` automatically when done

### Automation Flow

```
Browser Opens
    ↓
Google Cloud Console → Get Client ID & Secret
    ↓
Google Ads → Get Developer Token
    ↓
OAuth Playground → Get Refresh Token
    ↓
Update google-ads.yaml → All credentials saved!
```

---

## 📖 Documentation

- **`QUICK_START_AUTOMATION.md`** - Quick start guide
- **`GET_CREDENTIALS_GUIDE.md`** - Detailed manual steps (if automation fails)
- **`browser_automation_plan.md`** - Technical automation details
- **`CREDENTIALS_COLLECTION_PLAN.md`** - Execution checklist
- **`AUTOMATION_READY.md`** - Setup summary

---

## 🔧 Manual Steps You'll Need to Do

The script pauses and prompts you for:

1. **Select Google Cloud Project** - Choose from dropdown
2. **Create OAuth Credentials** - Click "CREATE CREDENTIALS" → "OAuth client ID"
3. **Configure Consent Screen** - Fill form if prompted (first time only)
4. **Select MCC Account** - Choose 211-993-1898 if prompted
5. **Sign In** - Authenticate with Google accounts
6. **Approve Permissions** - Allow OAuth access to Google Ads API
7. **Paste Credentials** - If auto-extraction fails (rare)

---

## ✅ After Collection

Once credentials are collected:

1. **Verify Setup**:
   ```bash
   python3 test_server.py
   ```

2. **Test MCP Connection**:
   ```bash
   claude mcp list
   ```
   Should show: `google-ads: ✓ Connected`

3. **Run Test Suite**:
   ```bash
   bash test_mcc_integration.sh
   ```

---

## 🆘 Troubleshooting

### Playwright Not Installed
```bash
bash setup_automation.sh
```

### Script Can't Find Elements
- Script will prompt you to navigate manually
- Press ENTER when on correct page
- Script continues automatically

### Credentials Not Extracted
- Script will ask you to paste manually
- Copy from browser and paste when prompted

### Need Manual Steps
See `GET_CREDENTIALS_GUIDE.md` for complete manual instructions

---

## 📁 Files

- `collect_credentials_automated.py` - Main automation script
- `setup_automation.sh` - Setup script
- `requirements-automation.txt` - Python dependencies
- `google-ads.yaml` - Configuration file (will be updated automatically)

---

## 🎉 Ready to Go!

Run these commands:

```bash
cd /Users/home/aimacpro/7_tools/mcp_tools/servers/google_ads_mcp
bash setup_automation.sh
python3 collect_credentials_automated.py
```

The script will handle everything and update your config automatically!

