# How to Actually Use the LLM Integration

**This guide shows you exactly what to do, step by step.**

---

## Step 1: Start Your LLM

### If You Have LLM Studio:

1. **Open LLM Studio** (the application)
2. **Load a model** (click "Load Model" and pick one, like Llama 3)
3. **Start the API server**:
   - Look for "API Server" or "Server" in the menu
   - Click "Start Server" or enable it
   - Note the port number (usually `1234`)
   - Note the model name shown (like `llama-3-8b-instruct`)

### If You Have a Local FastAPI Backend:

1. **Start your FastAPI server**:
   ```bash
   # In the directory where your FastAPI app is
   python -m uvicorn main:app --port 8000
   ```

### If You Have Ollama:

1. **Start Ollama**:
   ```bash
   ollama serve
   ```

2. **Pull a model** (if you haven't):
   ```bash
   ollama pull llama3
   ```

---

## Step 2: Configure the Playwright MCP Server

### Option A: Set Environment Variables (Recommended)

**For LLM Studio:**
```bash
export LLM_TYPE=llm-studio
export LLM_BASE_URL=http://localhost:1234/v1
export LLM_MODEL=llama-3-8b-instruct  # Use the exact name from LLM Studio
```

**For Local FastAPI:**
```bash
export LLM_TYPE=local-api
export LLM_BASE_URL=http://localhost:8000
export LLM_MODEL=your-model-name
```

**For Ollama:**
```bash
export LLM_TYPE=ollama
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=llama3
```

### Option B: Create a `.env` File

Create a file called `.env` in the `playwright_mcp` directory:

```bash
# .env file
LLM_TYPE=llm-studio
LLM_BASE_URL=http://localhost:1234/v1
LLM_MODEL=llama-3-8b-instruct
```

Then load it when starting:
```bash
source .env
npm start
```

---

## Step 3: Start the Playwright MCP Server

```bash
cd 4_agents/browser_automation_agent/playwright/mcp
npm start
```

You should see:
```
✅ LLM Service initialized: llm-studio at http://localhost:1234/v1
```

If you see an error, check:
- Is your LLM server running?
- Is the port correct?
- Is the model name correct?

---

## Step 4: Use the New Tools

### What Are These Tools?

1. **`browser_generate_script`** - Tell it what you want in plain English, it generates Playwright code
2. **`browser_inspect`** - Look at any element on the page (like DevTools)
3. **`browser_evaluate`** - Run JavaScript code in the browser
4. **`browser_inject_script`** - Add custom JavaScript to pages

### Example 1: Generate a Script

**What you want to do:** "Fill the login form with username 'test' and password 'pass123', then click submit"

**How to use it:**
- If using MCP client, call the tool:
  ```json
  {
    "tool": "browser_generate_script",
    "arguments": {
      "description": "Fill the login form with username 'test' and password 'pass123', then click submit"
    }
  }
  ```

**What happens:**
1. The LLM generates Playwright code
2. The code is executed automatically
3. The task is completed

### Example 2: Inspect an Element

**What you want to do:** See all the details about a button

**How to use it:**
```json
{
  "tool": "browser_inspect",
  "arguments": {
    "selector": "button.submit"
  }
}
```

**What you get back:**
- All possible ways to select it (ID, class, XPath, etc.)
- Its styles, position, size
- Whether it's visible/enabled
- Its parent and children elements

### Example 3: Run JavaScript

**What you want to do:** Get the text of the first heading

**How to use it:**
```json
{
  "tool": "browser_evaluate",
  "arguments": {
    "code": "document.querySelector('h1').textContent"
  }
}
```

**What you get back:**
- The result of running that JavaScript
- Just like typing it in the browser console

### Example 4: Inject Custom Code

**What you want to do:** Add a custom function that highlights elements

**How to use it:**
```json
{
  "tool": "browser_inject_script",
  "arguments": {
    "code": "window.highlight = (selector) => { const el = document.querySelector(selector); if (el) el.style.outline = '3px solid red'; }",
    "runOnNewDocument": false
  }
}
```

**What happens:**
- The code is added to the page
- You can now use `window.highlight('button')` in evaluate

---

## Step 5: Test It Works

### Quick Test

1. **Start your LLM** (LLM Studio, FastAPI, or Ollama)
2. **Set environment variables** (see Step 2)
3. **Start Playwright MCP**:
   ```bash
   npm start
   ```
4. **Look for this message**:
   ```
   ✅ LLM Service initialized: llm-studio at http://localhost:1234/v1
   ```

If you see that, it's working!

### Test Script Generation

Try generating a simple script:
```json
{
  "tool": "browser_generate_script",
  "arguments": {
    "description": "Navigate to https://example.com"
  }
}
```

If it works, you'll see:
- Script generated message
- Navigation happens
- Success response

---

## Troubleshooting

### "LLM service not configured"

**Problem:** You didn't set the environment variables

**Fix:**
```bash
export LLM_TYPE=llm-studio
export LLM_BASE_URL=http://localhost:1234/v1
export LLM_MODEL=your-model-name
```

### "Connection refused" or "Cannot connect"

**Problem:** Your LLM server isn't running

**Fix:**
1. Check if LLM Studio/FastAPI/Ollama is running
2. Check the port number is correct
3. Try accessing the URL in your browser: `http://localhost:1234/v1/models` (should show your models)

### "Model not found"

**Problem:** Wrong model name

**Fix:**
1. Check LLM Studio for the exact model name
2. Or list models: `curl http://localhost:1234/v1/models`
3. Use the exact name shown

### Script Generation Returns Errors

**Problem:** Model might not support JSON mode or needs different prompt

**Fix:**
1. Try a simpler description first
2. Check if your model supports JSON output
3. Look at server logs for error details

---

## Real-World Example

**Scenario:** You want to automate logging into a website

**Step 1:** Navigate to the site
```json
{
  "tool": "browser_execute",
  "arguments": {
    "task": "Navigate to https://example.com/login"
  }
}
```

**Step 2:** Inspect the login form to see what selectors are available
```json
{
  "tool": "browser_inspect",
  "arguments": {
    "selector": "input[type='email']"
  }
}
```

**Step 3:** Generate a script to fill and submit
```json
{
  "tool": "browser_generate_script",
  "arguments": {
    "description": "Fill the email field with 'user@example.com', fill the password field with 'password123', and click the submit button"
  }
}
```

**Done!** The LLM generates the code and it runs automatically.

---

## What If I Don't Want to Use LLM?

**No problem!** Just don't set the environment variables. The other tools still work:
- `browser_execute` - Still works (uses rule-based parsing)
- `browser_inspect` - Still works
- `browser_evaluate` - Still works
- `browser_inject_script` - Still works

Only `browser_generate_script` requires LLM.

---

## Summary

1. **Start your LLM** (LLM Studio, FastAPI, or Ollama)
2. **Set 3 environment variables** (`LLM_TYPE`, `LLM_BASE_URL`, `LLM_MODEL`)
3. **Start Playwright MCP** (`npm start`)
4. **Use the tools** via MCP client or API

That's it! The LLM integration is now working.

