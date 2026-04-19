# Setup LM Studio for Playwright MCP

## Quick Setup (3 Steps)

### Step 1: Enable API Server in LM Studio

1. **Open LM Studio** (it's already running ✅)
2. **Go to Settings** (gear icon or Settings menu)
3. **Find "API Server" or "Server" section**
4. **Enable/Start the API Server**
   - Toggle it ON
   - Note the port number (usually 1234)
   - Make sure it says "Running" or "Active"

### Step 2: Load a Model (if not already loaded)

1. In LM Studio, click **"Load Model"** or go to the Models tab
2. **Select a model** (any model works - Llama 3, Mistral, etc.)
3. **Click "Load"** to load it into memory
4. **Note the model name** (shown in the UI)

### Step 3: Run the Setup Script

```bash
cd /Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp
./setup-llm.sh
```

This will:
- ✅ Detect LM Studio
- ✅ Find the API port
- ✅ List available models
- ✅ Create a `.env` file with the configuration

### Step 4: Start Playwright MCP

```bash
source .env
npm start
```

You should see: `✅ LLM Service initialized: llm-studio`

---

## Manual Setup (If Script Doesn't Work)

If the script can't detect your setup, do this manually:

### 1. Find Your API Port

In LM Studio, check the API Server settings. It's usually port **1234**.

### 2. Find Your Model Name

In LM Studio, look at the loaded model. The name is shown in the UI (e.g., `llama-3-8b-instruct`).

### 3. Set Environment Variables

```bash
export LLM_TYPE=llm-studio
export LLM_BASE_URL=http://localhost:1234/v1
export LLM_MODEL=your-model-name-here
```

Replace `your-model-name-here` with the actual model name from LM Studio.

### 4. Test It

```bash
curl http://localhost:1234/v1/models
```

You should see a JSON response with your models.

### 5. Start Playwright MCP

```bash
npm start
```

---

## Troubleshooting

### "API Server not accessible"

**Problem:** API server isn't started in LM Studio

**Fix:**
1. Open LM Studio
2. Go to Settings → API Server
3. Enable/Start the server
4. Wait a few seconds for it to start
5. Try the setup script again

### "No models found"

**Problem:** No model is loaded in LM Studio

**Fix:**
1. In LM Studio, click "Load Model"
2. Select a model
3. Click "Load"
4. Wait for it to load
5. Try the setup script again

### "Connection refused"

**Problem:** Wrong port number

**Fix:**
1. Check LM Studio Settings → API Server for the actual port
2. Update the `LLM_BASE_URL` to use the correct port
3. Or try common ports: 1234, 1235, 1236

---

## What Port Does LM Studio Use?

By default, LM Studio uses port **1234**, but you can change it in Settings.

To check what port it's using:
1. Open LM Studio
2. Go to Settings → API Server
3. Look for "Port" or "Server Port"
4. Use that port in your configuration

---

## Quick Test

After setup, test if it works:

```bash
# Test API is accessible
curl http://localhost:1234/v1/models

# Should return JSON with your models
```

If that works, you're all set! 🎉

