#!/bin/bash

# Auto-configure LLM for Playwright MCP
# This script detects LM Studio and sets up the environment

echo "🔍 Detecting LM Studio configuration..."
echo ""

# Check if LM Studio is running
if ! pgrep -f "LM Studio" > /dev/null; then
    echo "⚠️  LM Studio is not running."
    echo "   Please start LM Studio first, then run this script again."
    exit 1
fi

echo "✅ LM Studio is running"
echo ""

# Try common ports
PORTS=(1234 1235 1236 1237 1238)
API_PORT=""
API_URL=""

for port in "${PORTS[@]}"; do
    if curl -s "http://localhost:${port}/v1/models" > /dev/null 2>&1; then
        API_PORT=$port
        API_URL="http://localhost:${port}/v1"
        echo "✅ Found LM Studio API at port ${port}"
        break
    fi
done

if [ -z "$API_PORT" ]; then
    echo "⚠️  LM Studio API server is not accessible."
    echo ""
    echo "Please do the following:"
    echo "  1. Open LM Studio"
    echo "  2. Go to Settings → API Server"
    echo "  3. Enable/Start the API Server"
    echo "  4. Wait a few seconds for it to start"
    echo "  5. Run this script again"
    echo ""
    echo "Common ports to check: 1234, 1235, 1236"
    exit 1
fi

echo ""

# Get available models
echo "📋 Fetching available models..."
MODELS_JSON=$(curl -s "${API_URL}/models" 2>/dev/null)

if [ -z "$MODELS_JSON" ] || [ "$MODELS_JSON" = "null" ] || [ "$MODELS_JSON" = "[]" ]; then
    echo "⚠️  No models found or API returned empty response."
    echo ""
    echo "Please:"
    echo "  1. Load a model in LM Studio (click 'Load Model')"
    echo "  2. Wait for it to load"
    echo "  3. Run this script again"
    exit 1
fi

# Extract model name (try different JSON formats)
MODEL_NAME=$(echo "$MODELS_JSON" | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4)

# If that didn't work, try another format
if [ -z "$MODEL_NAME" ]; then
    MODEL_NAME=$(echo "$MODELS_JSON" | grep -o '"model":"[^"]*"' | head -1 | cut -d'"' -f4)
fi

# If still no model, try parsing as array
if [ -z "$MODEL_NAME" ]; then
    MODEL_NAME=$(echo "$MODELS_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0]['id'] if isinstance(data, list) and len(data) > 0 else '')" 2>/dev/null)
fi

if [ -z "$MODEL_NAME" ]; then
    echo "⚠️  Could not parse model name from API response."
    echo ""
    echo "API Response:"
    echo "$MODELS_JSON" | head -5
    echo ""
    echo "Please set LLM_MODEL manually:"
    echo "  export LLM_MODEL=your-model-name"
    echo ""
    echo "Or check LM Studio UI for the model name."
    exit 1
fi

echo "✅ Found model: ${MODEL_NAME}"
echo ""

# Create .env file
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

cat > "$ENV_FILE" << EOF
# Auto-generated LLM configuration for Playwright MCP
# Generated: $(date)
# 
# To use: source .env
# Then: npm start

LLM_TYPE=llm-studio
LLM_BASE_URL=${API_URL}
LLM_MODEL=${MODEL_NAME}
EOF

echo "✅ Configuration saved to: ${ENV_FILE}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Configuration:"
echo "  LLM_TYPE=llm-studio"
echo "  LLM_BASE_URL=${API_URL}"
echo "  LLM_MODEL=${MODEL_NAME}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To use this configuration:"
echo "  cd $(dirname "$ENV_FILE")"
echo "  source .env"
echo "  npm start"
echo ""
echo "Or set environment variables manually:"
echo "  export LLM_TYPE=llm-studio"
echo "  export LLM_BASE_URL=${API_URL}"
echo "  export LLM_MODEL=${MODEL_NAME}"
