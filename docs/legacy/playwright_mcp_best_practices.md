# Playwright MCP Best Practices for AI-Driven Browser Automation

## The State Persistence Problem

Your current `BrowserAutomationAgent.ts:140-164` creates a **new browser context** for each task, causing:
- ❌ Lost authentication cookies
- ❌ Lost localStorage/sessionStorage
- ❌ Lost browser state between tasks
- ❌ Need to re-authenticate constantly

## Solution: Persistent Browser Context Pattern

### 1. Storage State Persistence

```typescript
/**
 * Enhanced Browser Automation Agent with Persistent State
 */
import { chromium, Browser, BrowserContext, Page } from 'playwright';
import * as fs from 'fs/promises';
import * as path from 'path';

export class PersistentBrowserAgent {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;

  // Critical: Storage state file path
  private readonly storageStatePath: string;
  private readonly contextOptions: any;

  constructor(config: {
    agentId: string;
    storageDir?: string;
    headless?: boolean;
  }) {
    // Store state per agent instance
    const stateDir = config.storageDir || path.join(__dirname, '.browser-state');
    this.storageStatePath = path.join(stateDir, `${config.agentId}-state.json`);

    this.contextOptions = {
      viewport: { width: 1920, height: 1080 },
      headless: config.headless ?? false,
      // Critical: Enable storage state
      storageState: undefined // Will be loaded in initializeBrowser
    };
  }

  /**
   * Initialize browser WITH persistent state
   */
  async initializeBrowser(): Promise<void> {
    // Launch browser once
    if (!this.browser) {
      this.browser = await chromium.launch({
        headless: this.contextOptions.headless,
        // Keep browser alive between tasks
        timeout: 0
      });
    }

    // Load existing storage state if available
    let storageState = undefined;
    try {
      const stateExists = await fs.access(this.storageStatePath)
        .then(() => true)
        .catch(() => false);

      if (stateExists) {
        storageState = JSON.parse(
          await fs.readFile(this.storageStatePath, 'utf-8')
        );
        console.log('✅ Loaded persistent browser state');
      }
    } catch (error) {
      console.log('ℹ️  No existing state found, starting fresh');
    }

    // Create or reuse context with loaded state
    if (!this.context) {
      this.context = await this.browser.newContext({
        ...this.contextOptions,
        storageState // Apply saved cookies, localStorage, etc.
      });

      // Create initial page if needed
      if (!this.page) {
        this.page = await this.context.newPage();
      }
    }
  }

  /**
   * Save browser state after each task
   */
  async saveState(): Promise<void> {
    if (!this.context) return;

    try {
      // Extract all browser state
      const state = await this.context.storageState();

      // Ensure directory exists
      await fs.mkdir(path.dirname(this.storageStatePath), { recursive: true });

      // Save to file
      await fs.writeFile(
        this.storageStatePath,
        JSON.stringify(state, null, 2)
      );

      console.log('✅ Browser state saved');
    } catch (error) {
      console.error('❌ Failed to save state:', error);
    }
  }

  /**
   * Execute task with persistent state
   */
  async executeTask(task: AgentTask): Promise<TaskResult> {
    try {
      // Initialize browser with saved state
      await this.initializeBrowser();

      // Execute task (your existing logic)
      const result = await this.performTask(task);

      // CRITICAL: Save state after each task
      await this.saveState();

      return result;
    } catch (error) {
      // Save state even on error to preserve progress
      await this.saveState();
      throw error;
    }
  }

  /**
   * Clear saved state (logout/reset)
   */
  async clearState(): Promise<void> {
    try {
      await fs.unlink(this.storageStatePath);
      console.log('✅ Browser state cleared');
    } catch (error) {
      // File might not exist, that's ok
    }
  }

  /**
   * Proper cleanup - DON'T close browser between tasks!
   */
  async cleanup(persistent: boolean = false): Promise<void> {
    // Save final state before closing
    await this.saveState();

    if (!persistent) {
      // Full cleanup (end of session)
      if (this.page) await this.page.close();
      if (this.context) await this.context.close();
      if (this.browser) await this.browser.close();

      this.page = null;
      this.context = null;
      this.browser = null;
    } else {
      // Keep browser alive, just close page
      if (this.page) await this.page.close();
      this.page = null;
    }
  }
}
```

### 2. Page State Management Pattern

```typescript
/**
 * Maintain page state across navigations
 */
class PageStateManager {
  private sessionData: Map<string, any> = new Map();

  /**
   * Save state before navigation
   */
  async capturePageState(page: Page, key: string): Promise<void> {
    const state = await page.evaluate(() => {
      return {
        url: window.location.href,
        localStorage: { ...localStorage },
        sessionStorage: { ...sessionStorage },
        cookies: document.cookie,
        // Capture form data
        formData: Array.from(document.querySelectorAll('input, select, textarea'))
          .reduce((acc, el: any) => {
            if (el.name) acc[el.name] = el.value;
            return acc;
          }, {} as Record<string, any>)
      };
    });

    this.sessionData.set(key, state);
  }

  /**
   * Restore state after navigation
   */
  async restorePageState(page: Page, key: string): Promise<void> {
    const state = this.sessionData.get(key);
    if (!state) return;

    await page.evaluate((savedState) => {
      // Restore localStorage
      Object.entries(savedState.localStorage).forEach(([k, v]) => {
        localStorage.setItem(k, v as string);
      });

      // Restore sessionStorage
      Object.entries(savedState.sessionStorage).forEach(([k, v]) => {
        sessionStorage.setItem(k, v as string);
      });

      // Restore form data
      Object.entries(savedState.formData).forEach(([name, value]) => {
        const el = document.querySelector(`[name="${name}"]`) as HTMLInputElement;
        if (el) el.value = value as string;
      });
    }, state);
  }
}
```

## Natural Language Playwright MCP Integration

### 3. MCP Server Pattern for Playwright

```typescript
/**
 * Playwright MCP Server with Natural Language Support
 */
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

class PlaywrightMCPServer {
  private server: Server;
  private browserAgent: PersistentBrowserAgent;

  constructor() {
    this.server = new Server(
      {
        name: 'playwright-automation',
        version: '1.0.0'
      },
      {
        capabilities: {
          tools: {},
          resources: {}
        }
      }
    );

    this.browserAgent = new PersistentBrowserAgent({
      agentId: 'mcp-browser',
      storageDir: './.mcp-browser-state'
    });

    this.registerTools();
  }

  private registerTools(): void {
    // Natural language browser automation
    this.server.setRequestHandler('tools/call', async (request) => {
      if (request.params.name === 'browser_execute') {
        return await this.executeBrowserTask(request.params.arguments);
      }

      if (request.params.name === 'browser_state') {
        return await this.manageBrowserState(request.params.arguments);
      }

      throw new Error(`Unknown tool: ${request.params.name}`);
    });

    // List available tools
    this.server.setRequestHandler('tools/list', async () => {
      return {
        tools: [
          {
            name: 'browser_execute',
            description: 'Execute browser automation tasks using natural language',
            inputSchema: {
              type: 'object',
              properties: {
                task: {
                  type: 'string',
                  description: 'Natural language description of what to do in the browser'
                },
                url: {
                  type: 'string',
                  description: 'Starting URL (optional if continuing from current page)'
                },
                waitFor: {
                  type: 'string',
                  description: 'CSS selector to wait for before considering task complete'
                },
                extract: {
                  type: 'array',
                  items: { type: 'string' },
                  description: 'CSS selectors for data to extract and return'
                }
              },
              required: ['task']
            }
          },
          {
            name: 'browser_state',
            description: 'Manage browser state (save, restore, clear)',
            inputSchema: {
              type: 'object',
              properties: {
                action: {
                  type: 'string',
                  enum: ['save', 'restore', 'clear', 'status']
                },
                stateKey: {
                  type: 'string',
                  description: 'Optional key for named state checkpoints'
                }
              },
              required: ['action']
            }
          }
        ]
      };
    });
  }

  /**
   * Execute natural language browser task
   */
  private async executeBrowserTask(args: any): Promise<any> {
    const { task, url, waitFor, extract } = args;

    try {
      // Initialize with persistent state
      await this.browserAgent.initializeBrowser();

      // Navigate if URL provided
      if (url) {
        await this.browserAgent.page!.goto(url);
      }

      // Parse natural language task to actions
      const actions = await this.parseNaturalLanguageTask(task);

      // Execute actions
      for (const action of actions) {
        await this.executeAction(action);
      }

      // Wait for completion
      if (waitFor) {
        await this.browserAgent.page!.waitForSelector(waitFor);
      }

      // Extract data if requested
      let extractedData = {};
      if (extract && extract.length > 0) {
        extractedData = await this.extractData(extract);
      }

      // Save state after successful execution
      await this.browserAgent.saveState();

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Completed: ${task}`,
              data: extractedData,
              currentUrl: this.browserAgent.page!.url()
            }, null, 2)
          }
        ]
      };
    } catch (error: any) {
      // Still save state on error to preserve progress
      await this.browserAgent.saveState();

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error.message,
              currentUrl: this.browserAgent.page?.url()
            }, null, 2)
          }
        ],
        isError: true
      };
    }
  }

  /**
   * Parse natural language to Playwright actions
   */
  private async parseNaturalLanguageTask(task: string): Promise<Action[]> {
    const taskLower = task.toLowerCase();
    const actions: Action[] = [];

    // Click detection
    if (taskLower.includes('click')) {
      const buttonText = this.extractQuotedText(task) ||
                         this.extractAfterPhrase(task, 'click');
      actions.push({
        type: 'click',
        selector: `button:has-text("${buttonText}"), a:has-text("${buttonText}")`
      });
    }

    // Fill form detection
    if (taskLower.includes('fill') || taskLower.includes('enter')) {
      const fieldName = this.extractAfterPhrase(task, 'fill') ||
                        this.extractAfterPhrase(task, 'enter');
      const value = this.extractQuotedText(task);

      actions.push({
        type: 'fill',
        selector: `input[name*="${fieldName}"], input[placeholder*="${fieldName}"]`,
        value
      });
    }

    // Select detection
    if (taskLower.includes('select')) {
      const option = this.extractQuotedText(task);
      actions.push({
        type: 'select',
        selector: 'select',
        value: option
      });
    }

    // Wait detection
    if (taskLower.includes('wait')) {
      const duration = this.extractNumber(task) || 1000;
      actions.push({
        type: 'wait',
        duration
      });
    }

    return actions;
  }

  /**
   * Execute a single action
   */
  private async executeAction(action: Action): Promise<void> {
    const page = this.browserAgent.page!;

    switch (action.type) {
      case 'click':
        await page.click(action.selector!);
        break;

      case 'fill':
        await page.fill(action.selector!, action.value!);
        break;

      case 'select':
        await page.selectOption(action.selector!, action.value!);
        break;

      case 'wait':
        await page.waitForTimeout(action.duration!);
        break;

      case 'waitForSelector':
        await page.waitForSelector(action.selector!);
        break;
    }
  }

  /**
   * Extract data from page
   */
  private async extractData(selectors: string[]): Promise<Record<string, any>> {
    const page = this.browserAgent.page!;
    const data: Record<string, any> = {};

    for (const selector of selectors) {
      try {
        const elements = await page.$$(selector);
        const values = await Promise.all(
          elements.map(el => el.textContent())
        );
        data[selector] = values.filter(Boolean);
      } catch (error) {
        data[selector] = null;
      }
    }

    return data;
  }

  /**
   * Manage browser state
   */
  private async manageBrowserState(args: any): Promise<any> {
    const { action, stateKey } = args;

    try {
      switch (action) {
        case 'save':
          await this.browserAgent.saveState();
          return {
            content: [{
              type: 'text',
              text: JSON.stringify({ success: true, message: 'State saved' })
            }]
          };

        case 'clear':
          await this.browserAgent.clearState();
          return {
            content: [{
              type: 'text',
              text: JSON.stringify({ success: true, message: 'State cleared' })
            }]
          };

        case 'status':
          const hasState = await this.checkStateExists();
          return {
            content: [{
              type: 'text',
              text: JSON.stringify({
                success: true,
                hasPersistedState: hasState,
                currentUrl: this.browserAgent.page?.url()
              })
            }]
          };

        default:
          throw new Error(`Unknown action: ${action}`);
      }
    } catch (error: any) {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({ success: false, error: error.message })
        }],
        isError: true
      };
    }
  }

  // Helper methods
  private extractQuotedText(text: string): string | null {
    const match = text.match(/"([^"]+)"/);
    return match ? match[1] : null;
  }

  private extractAfterPhrase(text: string, phrase: string): string {
    const parts = text.toLowerCase().split(phrase);
    return parts[1]?.trim().split(' ')[0] || '';
  }

  private extractNumber(text: string): number | null {
    const match = text.match(/\d+/);
    return match ? parseInt(match[0]) : null;
  }

  private async checkStateExists(): Promise<boolean> {
    try {
      await fs.access(this.browserAgent['storageStatePath']);
      return true;
    } catch {
      return false;
    }
  }

  async start(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('Playwright MCP Server running on stdio');
  }
}

// Type definitions
interface Action {
  type: 'click' | 'fill' | 'select' | 'wait' | 'waitForSelector';
  selector?: string;
  value?: string;
  duration?: number;
}

// Start server
const server = new PlaywrightMCPServer();
server.start().catch(console.error);
```

### 4. MCP Configuration for Claude

```json
{
  "mcpServers": {
    "playwright-automation": {
      "type": "stdio",
      "command": "node",
      "args": [
        "/Users/home/aimacpro/4_agents/browser_automation_agent/playwright/mcp/dist/server.js"
      ],
      "env": {
        "BROWSER_STATE_DIR": "/Users/home/aimacpro/.browser-states"
      }
    }
  }
}
```

## Best Practices Summary

### ✅ DO: State Persistence

```typescript
// ✅ Save state after each task
await browserAgent.saveState();

// ✅ Load state before each task
await browserAgent.initializeBrowser(); // Auto-loads saved state

// ✅ Use storageState for authentication persistence
context = await browser.newContext({
  storageState: './saved-state.json'
});
```

### ❌ DON'T: Recreate Context

```typescript
// ❌ Don't create new context for each task
async executeTask() {
  this.context = await this.browser.newContext(); // Loses all state!
  // ...
}

// ❌ Don't close browser between tasks
await browser.close(); // Next task has to start over!

// ❌ Don't forget to save state
await task.execute();
return result; // State lost if crash happens!
```

### Best Practice Pattern

```typescript
/**
 * Production-ready browser automation pattern
 */
class ProductionBrowserAgent {
  // 1. Keep browser instance alive
  private browser: Browser;

  // 2. Reuse context with state
  private context: BrowserContext;

  // 3. Save state after EVERY operation
  async executeTask(task: Task): Promise<Result> {
    try {
      await this.initializeWithState();
      const result = await this.doWork(task);
      await this.saveState(); // Always save
      return result;
    } catch (error) {
      await this.saveState(); // Save even on error
      throw error;
    }
  }

  // 4. Graceful shutdown only at session end
  async shutdown(): Promise<void> {
    await this.saveState();
    await this.context.close();
    await this.browser.close();
  }
}
```

## Natural Language Integration

### Example Claude Conversation

```typescript
// User: "Click the login button and fill in my credentials"

// MCP Server receives:
{
  tool: 'browser_execute',
  arguments: {
    task: 'Click the login button and fill in username "john@example.com" and password "secret"'
  }
}

// Server parses to:
[
  { type: 'click', selector: 'button:has-text("Login")' },
  { type: 'fill', selector: 'input[name="username"]', value: 'john@example.com' },
  { type: 'fill', selector: 'input[name="password"]', value: 'secret' },
  { type: 'click', selector: 'button[type="submit"]' }
]

// After execution, state is saved automatically
// Next task can continue from logged-in state!
```

## Debugging State Issues

### Check State File

```bash
# View saved state
cat .browser-state/mcp-browser-state.json

# Output shows:
{
  "cookies": [...],
  "origins": [
    {
      "origin": "https://example.com",
      "localStorage": [
        { "name": "authToken", "value": "..." }
      ]
    }
  ]
}
```

### State Verification Tool

```typescript
async function verifyState(): Promise<void> {
  const agent = new PersistentBrowserAgent({ agentId: 'test' });
  await agent.initializeBrowser();

  // Check if authenticated
  const isLoggedIn = await agent.page!.evaluate(() => {
    return Boolean(localStorage.getItem('authToken'));
  });

  console.log('State valid:', isLoggedIn);
}
```

## Performance Optimization

### 1. Keep Browser Warm

```typescript
// Keep one browser instance for multiple agents
class BrowserPool {
  private static browser: Browser;

  static async getBrowser(): Promise<Browser> {
    if (!this.browser) {
      this.browser = await chromium.launch();
    }
    return this.browser;
  }

  static async createContext(stateFile: string): Promise<BrowserContext> {
    const browser = await this.getBrowser();
    let state;

    try {
      state = JSON.parse(await fs.readFile(stateFile, 'utf-8'));
    } catch {}

    return browser.newContext({ storageState: state });
  }
}
```

### 2. Selective State Saving

```typescript
// Only save state when it changed
private stateHash: string = '';

async saveStateIfChanged(): Promise<void> {
  const currentState = await this.context.storageState();
  const currentHash = this.hashState(currentState);

  if (currentHash !== this.stateHash) {
    await fs.writeFile(this.storageStatePath, JSON.stringify(currentState));
    this.stateHash = currentHash;
  }
}
```

## Migration Guide

### Update Your BrowserAutomationAgent

1. **Add state persistence**:
```typescript
// In constructor:
this.storageStatePath = path.join(__dirname, '.state', `${agentId}.json`);

// In initializeBrowser:
const state = await this.loadState();
this.context = await browser.newContext({ storageState: state });

// After executeTask:
await this.saveState();
```

2. **Don't close browser between tasks**:
```typescript
// Remove from executeTask:
// await this.cleanup(); // ❌

// Only cleanup at session end:
await agent.shutdown(); // ✅
```

3. **Handle page reloads properly**:
```typescript
// Save state before reload
await this.saveState();

await Promise.all([
  page.waitForNavigation(),
  page.click('button')
]);

// State persists through reload automatically
```

## Conclusion

The key to persistent Playwright automation with AI:

1. **One browser instance** for the entire session
2. **Save `storageState`** after every task
3. **Load `storageState`** before every task
4. **Don't close browser** between related tasks
5. **Natural language parsing** maps to Playwright actions
6. **MCP server** exposes browser automation to Claude

This pattern gives you:
- ✅ Persistent authentication
- ✅ Maintained session state
- ✅ Natural language control
- ✅ Robust error recovery
- ✅ Multi-task workflows

Now your browser automation will maintain state across tasks, and Claude can drive it with natural language through the MCP server!
