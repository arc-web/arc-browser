# LLM Setup for AI Script Generation

## Quick Start

### Option 1: LLM Studio (Recommended)

1. **Start LLM Studio**
   - Launch LLM Studio application
   - Load your preferred model (e.g., Llama 3, Mistral, etc.)

2. **Enable API Server**
   - Go to Settings → API Server
   - Enable "Start API Server"
   - Note the port (usually 1234)

3. **Set Environment Variables**
   ```bash
   export LLM_TYPE=llm-studio
   export LLM_BASE_URL=http://localhost:1234/v1
   export LLM_MODEL=your-model-name  # Check LLM Studio UI for exact name
   ```

4. **Start Playwright MCP Server**
   ```bash
   npm start
   ```

### Option 2: Local FastAPI Backend

If you have a FastAPI backend at `http://localhost:8000/chat`:

```bash
export LLM_TYPE=local-api
export LLM_BASE_URL=http://localhost:8000
export LLM_MODEL=your-model-name
```

### Option 3: Ollama

```bash
export LLM_TYPE=ollama
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=llama3  # or your model name
```

### Option 4: OpenAI

```bash
export LLM_TYPE=openai
export LLM_API_KEY=sk-...
export LLM_MODEL=gpt-3.5-turbo
```

### Disable LLM (Default)

If LLM is not configured, script generation features will be disabled:

```bash
# No environment variables needed
# LLM features will be unavailable
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_TYPE` | Type of LLM: `llm-studio`, `local-api`, `ollama`, `openai`, or `disabled` | `disabled` |
| `LLM_BASE_URL` | Base URL for LLM API | Varies by type |
| `LLM_API_KEY` | API key (usually not needed for local LLMs) | `not-needed` |
| `LLM_MODEL` | Model name | `gpt-3.5-turbo` |

## Usage

Once configured, you can use the new MCP tools:

### 1. Generate Script from Natural Language

```json
{
  "tool": "browser_generate_script",
  "arguments": {
    "description": "Fill the login form with username 'test' and password 'pass123', then click submit"
  }
}
```

### 2. Inspect Element

```json
{
  "tool": "browser_inspect",
  "arguments": {
    "selector": "button.submit"
  }
}
```

### 3. Execute JavaScript

```json
{
  "tool": "browser_evaluate",
  "arguments": {
    "code": "document.querySelector('h1').textContent"
  }
}
```

### 4. Inject Script

```json
{
  "tool": "browser_inject_script",
  "arguments": {
    "code": "window.myFunction = () => console.log('Hello!');",
    "runOnNewDocument": true
  }
}
```

## Testing

Test your LLM setup:

```bash
# Test LLM connection
curl -X POST http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "your-model-name",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Troubleshooting

### LLM Not Connecting

1. Check if LLM server is running
2. Verify `LLM_BASE_URL` is correct
3. Check `LLM_MODEL` matches your model name
4. Look for error messages in server logs

### Script Generation Fails

1. Ensure LLM is properly configured
2. Check model supports JSON output
3. Verify model has enough context length
4. Try simpler descriptions first

### Self-Healing Not Working

1. Ensure LLM service is enabled
2. Check error messages are being passed correctly
3. Verify model can understand Playwright code

## Notes

- **No API Keys**: Local LLMs (LLM Studio, Ollama) don't require real API keys
- **Model Name**: Check your LLM UI for the exact model name
- **JSON Mode**: Recommended for better script parsing
- **Temperature**: Lower (0.2-0.3) for more deterministic code generation

