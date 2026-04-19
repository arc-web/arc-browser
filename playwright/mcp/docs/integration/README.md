# Playwright + AI Reasoning Integration

Intelligent browser automation that combines Playwright MCP with AI reasoning for autonomous error handling and selective human-in-the-loop.

## Quick Start

```typescript
import { AIReasoningAgent } from './ai-reasoning-agent';

const agent = new AIReasoningAgent({
  llm: 'gpt-4o',
  playwrightMCPUrl: 'http://localhost:3000'
});

// Execute complex task with AI reasoning
const result = await agent.executeTask(
  "Complete checkout on example.com with item in cart"
);

// Agent will:
// - Plan the task
// - Execute with error recovery
// - Ask human only when necessary
// - Complete autonomously otherwise
```

## Features

- ✅ AI-powered task planning
- ✅ Autonomous error recovery
- ✅ Intelligent retry strategies
- ✅ Selective human-in-the-loop
- ✅ Context-aware decision making
- ✅ State persistence

## Architecture

See `terminalprogress/playwright_ai_reasoning_guide.md` for complete architecture and implementation details.

