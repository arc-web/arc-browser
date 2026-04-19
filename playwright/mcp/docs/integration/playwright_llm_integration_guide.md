# Playwright MCP + Local LLM Integration Guide

**Date**: 2025-01-21
**Focus**: Integrating Local LLM / LLM Studio with Playwright MCP for AI Script Generation

---

## 🎯 Overview

Yes, your local LLM and LLM Studio setup would work perfectly for AI script generation! Here's how to integrate it.

---

## 🔌 Integration Options

### Option 1: LLM Studio (Recommended)

**LLM Studio** typically exposes an OpenAI-compatible API at `http://localhost:1234/v1`

**Setup**:
1. Start LLM Studio
2. Load your model
3. Enable API server (usually port 1234)
4. Use OpenAI-compatible client

### Option 2: Local FastAPI Backend

You already have a FastAPI backend at `http://localhost:8000/chat` (from your codebase)

### Option 3: Ollama

If you're using Ollama, it exposes an API at `http://localhost:11434`

---

## 🚀 Implementation

### 1. Create LLM Service Adapter

```typescript
// 4_agents/browser_automation_agent/playwright/mcp/src/llm-service.ts

import OpenAI from 'openai';

export interface LLMConfig {
  type: 'llm-studio' | 'local-api' | 'ollama' | 'openai';
  baseURL?: string;
  apiKey?: string;
  model?: string;
}

export class LLMService {
  private client: OpenAI | null = null;
  private config: LLMConfig;

  constructor(config: LLMConfig) {
    this.config = config;
    this.initialize();
  }

  private initialize() {
    const baseURL = this.getBaseURL();
    const apiKey = this.config.apiKey || 'not-needed'; // Local LLMs often don't need real keys

    this.client = new OpenAI({
      baseURL,
      apiKey,
    });
  }

  private getBaseURL(): string {
    switch (this.config.type) {
      case 'llm-studio':
        return this.config.baseURL || 'http://localhost:1234/v1';
      case 'local-api':
        return this.config.baseURL || 'http://localhost:8000';
      case 'ollama':
        return this.config.baseURL || 'http://localhost:11434/v1';
      case 'openai':
        return 'https://api.openai.com/v1';
      default:
        throw new Error(`Unknown LLM type: ${this.config.type}`);
    }
  }

  /**
   * Generate Playwright script from natural language
   */
  async generateScript(
    description: string,
    context: {
      currentUrl?: string;
      pageTitle?: string;
      availableElements?: any[];
    } = {}
  ): Promise<{
    code: string;
    explanation: string;
    selectors: string[];
    estimatedTime: string;
  }> {
    if (!this.client) {
      throw new Error('LLM client not initialized');
    }

    const prompt = this.buildScriptGenerationPrompt(description, context);

    try {
      const response = await this.client.chat.completions.create({
        model: this.config.model || 'gpt-3.5-turbo', // Model name for local LLMs
        messages: [
          {
            role: 'system',
            content: `You are an expert Playwright automation engineer. Generate TypeScript Playwright code that is:
- Correct and executable
- Uses Playwright's Locator API
- Includes proper error handling
- Uses smart waits
- Returns results

Always respond with valid JSON in this format:
{
  "code": "// Generated Playwright code here",
  "explanation": "What the script does",
  "selectors": ["selector1", "selector2"],
  "estimatedTime": "5 seconds"
}`
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.3, // Lower temperature for more deterministic code
        max_tokens: 2000,
        response_format: { type: 'json_object' } // Force JSON response
      });

      const content = response.choices[0]?.message?.content;
      if (!content) {
        throw new Error('No response from LLM');
      }

      // Parse JSON response
      const result = JSON.parse(content);
      return result;
    } catch (error) {
      throw new Error(`LLM script generation failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Self-heal: Regenerate script on failure
   */
  async selfHeal(
    failedScript: string,
    error: Error,
    currentPageState: {
      url: string;
      htmlStructure?: string;
      elements?: any[];
    }
  ): Promise<string> {
    if (!this.client) {
      throw new Error('LLM client not initialized');
    }

    const prompt = `This Playwright script failed:
\`\`\`typescript
${failedScript}
\`\`\`

Error: ${error.message}

Current page state:
- URL: ${currentPageState.url}
- Available elements: ${JSON.stringify(currentPageState.elements || [])}

Generate a fixed version that:
1. Updates selectors if they changed
2. Adds proper waits
3. Handles the error condition
4. Uses alternative approaches if needed

Respond with ONLY the fixed TypeScript Playwright code, no explanations.`;

    try {
      const response = await this.client.chat.completions.create({
        model: this.config.model || 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: 'You are an expert at fixing broken Playwright scripts. Return only the fixed code, no explanations.'
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        temperature: 0.2,
        max_tokens: 2000
      });

      const content = response.choices[0]?.message?.content;
      if (!content) {
        throw new Error('No response from LLM');
      }

      // Extract code from markdown code blocks if present
      const codeMatch = content.match(/```typescript\n([\s\S]*?)\n```/) || 
                       content.match(/```\n([\s\S]*?)\n```/);
      return codeMatch ? codeMatch[1] : content.trim();
    } catch (error) {
      throw new Error(`LLM self-healing failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  private buildScriptGenerationPrompt(
    description: string,
    context: any
  ): string {
    return `Generate a Playwright script to: ${description}

Current context:
${context.currentUrl ? `- URL: ${context.currentUrl}` : ''}
${context.pageTitle ? `- Page title: ${context.pageTitle}` : ''}
${context.availableElements ? `- Available elements: ${JSON.stringify(context.availableElements)}` : ''}

Generate TypeScript Playwright code that:
1. Uses Playwright's Locator API (getByRole, getByText, etc.)
2. Includes error handling
3. Uses smart waits (waitForLoadState, waitForSelector)
4. Returns result

Response format (JSON):
{
  "code": "// Generated Playwright code",
  "explanation": "What the script does",
  "selectors": ["selector1", "selector2"],
  "estimatedTime": "5 seconds"
}`;
  }
}
```

### 2. Integrate with Browser Agent

```typescript
// 4_agents/browser_automation_agent/playwright/mcp/src/browser-agent.ts

import { LLMService, LLMConfig } from './llm-service.js';

export class PersistentBrowserAgent {
  // ... existing code ...
  
  private llmService: LLMService | null = null;
  private scriptCache: Map<string, string> = new Map();

  /**
   * Initialize LLM service
   */
  initializeLLM(config: LLMConfig): void {
    this.llmService = new LLMService(config);
  }

  /**
   * Generate and execute script from natural language
   */
  async executeTaskWithAIScript(
    description: string
  ): Promise<any> {
    if (!this.llmService) {
      throw new Error('LLM service not initialized. Call initializeLLM() first.');
    }

    // Check cache
    const taskHash = this.hashTask(description);
    let script = this.scriptCache.get(taskHash);

    if (!script) {
      // Generate script from natural language
      console.error('🤖 Generating script from natural language...');
      
      const page = await this.getPage();
      const context = {
        currentUrl: page.url(),
        pageTitle: await page.title().catch(() => 'unknown'),
        availableElements: await this.getAvailableElements(page)
      };

      const generated = await this.llmService.generateScript(description, context);
      script = generated.code;
      
      // Cache script
      this.scriptCache.set(taskHash, script);
      console.error(`✅ Script generated: ${generated.explanation}`);
    }

    // Execute generated script
    try {
      const result = await this.executeGeneratedScript(script);
      return result;
    } catch (error) {
      // Self-heal: Regenerate script on failure
      console.error('🔧 Script failed, self-healing...');
      
      const page = await this.getPage();
      const pageState = {
        url: page.url(),
        elements: await this.getAvailableElements(page)
      };

      const healedScript = await this.llmService.selfHeal(
        script,
        error as Error,
        pageState
      );

      // Update cache
      this.scriptCache.set(taskHash, healedScript);

      // Retry with healed script
      console.error('🔄 Retrying with healed script...');
      return await this.executeGeneratedScript(healedScript);
    }
  }

  /**
   * Execute generated Playwright script
   */
  private async executeGeneratedScript(script: string): Promise<any> {
    const page = await this.getPage();

    // Parse script and convert to actions
    // (Simplified - in reality, you'd parse TypeScript)
    const actions = this.parseScriptToActions(script);

    for (const action of actions) {
      await this.executeActionIntelligently(action);
    }

    return { success: true };
  }

  /**
   * Get available elements on page (for context)
   */
  private async getAvailableElements(page: Page): Promise<any[]> {
    return await page.evaluate(() => {
      const elements = Array.from(document.querySelectorAll('button, a, input, select, textarea'));
      return elements.slice(0, 20).map(el => ({
        tag: el.tagName,
        id: el.id,
        className: el.className,
        textContent: el.textContent?.trim().substring(0, 50),
        type: el.getAttribute('type'),
        role: el.getAttribute('role')
      }));
    });
  }

  /**
   * Hash task description for caching
   */
  private hashTask(description: string): string {
    // Simple hash (use crypto for production)
    return Buffer.from(description).toString('base64');
  }

  /**
   * Parse TypeScript script to actions (simplified)
   */
  private parseScriptToActions(script: string): BrowserAction[] {
    // This is simplified - in reality, you'd use a TypeScript parser
    // For now, extract common patterns
    
    const actions: BrowserAction[] = [];
    
    // Extract navigate
    const navMatch = script.match(/goto\(['"]([^'"]+)['"]\)/);
    if (navMatch) {
      actions.push({ type: 'navigate', url: navMatch[1] });
    }

    // Extract clicks
    const clickMatches = script.matchAll(/click\(\)/g);
    // ... parse more patterns

    return actions;
  }
}
```

### 3. Configuration

```typescript
// 4_agents/browser_automation_agent/playwright/mcp/src/config.ts

export interface PlaywrightMCPConfig {
  // ... existing config ...
  llm?: {
    type: 'llm-studio' | 'local-api' | 'ollama' | 'openai';
    baseURL?: string;
    apiKey?: string;
    model?: string;
  };
}

// Usage
const config: PlaywrightMCPConfig = {
  // ... other config ...
  llm: {
    type: 'llm-studio', // or 'local-api', 'ollama', 'openai'
    baseURL: 'http://localhost:1234/v1', // LLM Studio default
    model: 'llama-3-8b-instruct', // Your model name
  }
};

// Initialize
browserAgent.initializeLLM(config.llm);
```

---

## 🔧 Setup Instructions

### For LLM Studio

1. **Start LLM Studio**
   ```bash
   # Launch LLM Studio application
   ```

2. **Load Model**
   - Open LLM Studio
   - Load your preferred model (e.g., Llama 3, Mistral, etc.)

3. **Enable API Server**
   - Go to Settings → API Server
   - Enable "Start API Server"
   - Note the port (usually 1234)

4. **Configure Playwright MCP**
   ```typescript
   browserAgent.initializeLLM({
     type: 'llm-studio',
     baseURL: 'http://localhost:1234/v1',
     model: 'your-model-name' // Check LLM Studio for exact name
   });
   ```

### For Local FastAPI Backend

If you have a FastAPI backend at `http://localhost:8000/chat`:

```typescript
// Create adapter for your FastAPI format
class FastAPILLMService extends LLMService {
  async generateScript(description: string, context: any): Promise<any> {
    const response = await fetch('http://localhost:8000/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: this.buildScriptGenerationPrompt(description, context)
      })
    });

    const data = await response.json();
    // Parse your FastAPI response format
    return JSON.parse(data.response);
  }
}
```

### For Ollama

```typescript
browserAgent.initializeLLM({
  type: 'ollama',
  baseURL: 'http://localhost:11434/v1',
  model: 'llama3' // or your model name
});
```

---

## 📝 Usage Examples

### Generate Script from Natural Language

```typescript
// Initialize LLM
browserAgent.initializeLLM({
  type: 'llm-studio',
  baseURL: 'http://localhost:1234/v1',
  model: 'llama-3-8b-instruct'
});

// Generate and execute script
await browserAgent.executeTaskWithAIScript(
  'Navigate to example.com, fill the search box with "Playwright", and click search'
);
```

### Self-Healing on Failure

```typescript
// If script fails, it automatically:
// 1. Detects the error
// 2. Sends error + page state to LLM
// 3. Gets fixed script
// 4. Retries automatically
```

---

## 🎯 How It Works

1. **User Request**: "Fill the form and submit"
2. **LLM Generation**: 
   - Sends prompt to your local LLM
   - Gets generated Playwright code
   - Caches for reuse
3. **Execution**: 
   - Parses generated code
   - Converts to browser actions
   - Executes intelligently
4. **Self-Healing** (if fails):
   - Sends error + page state to LLM
   - Gets fixed script
   - Retries automatically

---

## 🔍 Testing Your Setup

```typescript
// Test script
const testLLM = async () => {
  const llm = new LLMService({
    type: 'llm-studio',
    baseURL: 'http://localhost:1234/v1',
    model: 'your-model-name'
  });

  const result = await llm.generateScript(
    'Click the submit button',
    { currentUrl: 'https://example.com' }
  );

  console.log('Generated code:', result.code);
  console.log('Explanation:', result.explanation);
};

testLLM();
```

---

## 💡 Key Points

1. **Yes, your local LLM works!** ✅
   - LLM Studio exposes OpenAI-compatible API
   - Your FastAPI backend can be adapted
   - Ollama also works

2. **No API keys needed** (usually)
   - Local LLMs don't require real API keys
   - Use placeholder like `'not-needed'`

3. **Model name matters**
   - Check LLM Studio for exact model name
   - Use the name shown in LLM Studio UI

4. **JSON mode recommended**
   - Use `response_format: { type: 'json_object' }`
   - Makes parsing easier

5. **Temperature settings**
   - Lower (0.2-0.3) for code generation
   - More deterministic output

---

## 🚀 Next Steps

1. **Install OpenAI SDK** (for compatibility):
   ```bash
   cd 4_agents/browser_automation_agent/playwright/mcp
   npm install openai
   ```

2. **Add LLM service**:
   - Create `src/llm-service.ts`
   - Integrate with `browser-agent.ts`

3. **Test with your LLM**:
   - Start LLM Studio
   - Test script generation
   - Verify it works

4. **Add MCP tool**:
   - Expose `browser_generate_script` tool
   - Allow natural language → script generation

---

**Status**: ✅ Ready to implement
**Your Setup**: ✅ Compatible (LLM Studio / Local API)
**Next**: Implement LLM service integration

