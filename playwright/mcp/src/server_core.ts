#!/usr/bin/env node

/**
 * Playwright MCP Server Core
 * Contains server logic without transport-specific code
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool
} from '@modelcontextprotocol/sdk/types.js';

import { PersistentBrowserAgent } from './browser_agent.js';
import { IntentParser } from './intent_parser.js';
import type { ExecuteTaskArgs, StateManagementArgs, TaskResult } from './types.js';
import { LLMConfig } from './llm_service.js';
import * as path from 'path';

export class PlaywrightMCPServer {
  private server: Server;
  private browserAgent: PersistentBrowserAgent;
  private intentParser: IntentParser;

  constructor() {
    this.server = new Server(
      {
        name: 'playwright-automation',
        version: '1.0.0'
      },
      {
        capabilities: {
          tools: {}
        }
      }
    );

    // Parse extension paths from environment variable (comma-separated)
    const extensionPaths = process.env.BROWSER_EXTENSION_PATHS
      ? process.env.BROWSER_EXTENSION_PATHS.split(',').map(p => p.trim()).filter(Boolean)
      : undefined;

    this.browserAgent = new PersistentBrowserAgent({
      agentId: 'mcp-browser',
      stateDir: process.env.BROWSER_STATE_DIR || './.mcp-browser-state',
      headless: process.env.HEADLESS !== 'false',
      // Enforce persistent user data directory by default to ensure session reuse
      userDataDir: process.env.BROWSER_USER_DATA_DIR || path.join(process.env.HOME || '.', '.browser-profile'),
      extensionPaths: extensionPaths // Paths to extension directories
    });

    this.intentParser = new IntentParser();

    // Initialize LLM service if configured
    const llmConfig = this.getLLMConfig();
    if (llmConfig && llmConfig.type !== 'disabled') {
      this.browserAgent.initializeLLM(llmConfig);
    }

    this.setupHandlers();
  }

  private getLLMConfig(): LLMConfig {
    const type = (process.env.LLM_TYPE || 'disabled') as LLMConfig['type'];
    if (type === 'disabled') {
      return { type: 'disabled' };
    }

    return {
      type,
      baseURL: process.env.LLM_BASE_URL,
      apiKey: process.env.LLM_API_KEY,
      model: process.env.LLM_MODEL
    };
  }

  getServer(): Server {
    return this.server;
  }

  private setupHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      const tools: Tool[] = [
        {
          name: 'browser_execute',
          description: `Browser automation tool for web interactions. Use when:
- You need to interact with web pages (click buttons, fill forms, navigate)
- You need to extract data from dynamic/JavaScript-rendered pages
- You need to maintain login sessions across multiple actions
- You need to handle pages that require JavaScript execution

IMPORTANT: Browser state (cookies, auth, localStorage) persists automatically across ALL calls. You don't need to re-authenticate between calls. If a task fails, state is still saved, so you can retry or continue from the current page.

Multi-step tasks: You can combine multiple actions in a single call. Example: "Navigate to example.com, fill email with user@example.com, fill password with secret123, and click login" - this is ONE call that does all steps.

Error handling: If you get an error, check the error message. Transient errors (element not found, timeout) usually mean the page is still loading - wait 1-2 seconds and retry. Permanent errors (page not found, invalid URL) mean the task can't be completed - don't retry, report to user.

CONTEXT AWARENESS:
If the user's request is complex or involves specific apps (like ClickUp, Jira, etc.), you SHOULD first use the 'context7' MCP tool (if available) to get "click-by-click" guidance or library docs. Then, pass that guidance into the 'context' parameter of this tool. This helps the browser agent understand exactly what to do.`,
          inputSchema: {
            type: 'object',
            properties: {
              task: {
                type: 'string',
                description: `Natural language description of what to do. You can combine multiple actions:
- Single action: "Click the login button"
- Multiple actions: "Navigate to https://example.com, fill email with user@example.com, and click submit"
- With extraction: "Extract all product names from the page"
- With screenshot: "Take a screenshot of the current page"

Examples:
- "Click the login button"
- "Fill username with john@example.com and password with secret123"
- "Navigate to https://example.com"
- "Select Premium from the dropdown"
- "Wait 3 seconds"
- "Extract all text from h1 elements"`
              },
              context: {
                type: 'string',
                description: 'Optional guidance or context from external tools (like context7) to help the agent understand the task. Example: "Click the profile icon, then settings, then API keys".'
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
              },
              screenshot: {
                type: 'boolean',
                description: 'Take a screenshot after executing the task'
              }
            },
            required: ['task']
          }
        },
        {
          name: 'browser_state',
          description: `Check or manage browser state (cookies, localStorage, authentication). 

IMPORTANT: Use this tool PROACTIVELY, not just when explicitly asked!

Use "status" when:
- User asks about current page/authentication ("where am I?", "am I logged in?")
- A task failed and you need to debug (check if still on expected page)
- Before starting a new workflow (verify if already logged in - might save steps!)
- When you're unsure about current browser context
- After an error to understand what state was preserved

The "status" action returns: { hasPersistedState, currentUrl, pageTitle } - use this information to make better decisions about what to do next.

Use "clear" when:
- User explicitly wants to logout or start fresh
- Starting a completely new session unrelated to previous work

NOTE: State saves AUTOMATICALLY after every browser_execute call. You don't need to manually save. The "save" action is rarely needed.`,
          inputSchema: {
            type: 'object',
            properties: {
              action: {
                type: 'string',
                enum: ['save', 'clear', 'status'],
                description: `"status": Check if browser has saved state and get current URL/page info
"clear": Clear all saved state (logout, start fresh session)
"save": Force save state immediately (rarely needed - state saves automatically)`
              }
            },
            required: ['action']
          }
        },
        {
          name: 'browser_inspect',
          description: `Inspect DOM element with full details (selectors, styles, relationships). Like using browser DevTools.

USE THIS when:
- You need to find the right selector for an element
- An element isn't being found and you need to debug
- You need to understand element structure before interacting with it
- User asks about page structure or element details

This tool helps you understand the page better so you can use browser_execute more effectively.`,
          inputSchema: {
            type: 'object',
            properties: {
              selector: {
                type: 'string',
                description: 'CSS selector for element to inspect. Use this to understand element structure and find better selectors.'
              }
            },
            required: ['selector']
          }
        },
        {
          name: 'browser_evaluate',
          description: `Execute JavaScript code in browser context (like browser console). Can run any JavaScript on the page.

USE THIS when:
- You need to extract complex data that requires JavaScript
- You need to interact with page in ways browser_execute can't handle
- You need to check page state or run custom logic
- User asks for something that requires custom JavaScript

Note: For most tasks, browser_execute is simpler and better. Use this only when you need custom JavaScript logic.`,
          inputSchema: {
            type: 'object',
            properties: {
              code: {
                type: 'string',
                description: 'JavaScript code to execute in browser context. Can access page variables, DOM, etc.'
              },
              args: {
                type: 'array',
                description: 'Arguments to pass to code (optional)'
              }
            },
            required: ['code']
          }
        },
        {
          name: 'browser_generate_script',
          description: `Generate Playwright script from natural language using AI. Requires LLM to be configured.

USE THIS when:
- You need to generate a complex Playwright script
- User asks for a script to be generated
- You want to see the Playwright code equivalent of a task

Note: For most tasks, just use browser_execute directly. This tool is for when you specifically need the generated script code.`,
          inputSchema: {
            type: 'object',
            properties: {
              description: {
                type: 'string',
                description: 'Natural language description of what the script should do. Example: "Fill the login form and submit"'
              }
            },
            required: ['description']
          }
        },
        {
          name: 'browser_inject_script',
          description: `Inject JavaScript script into page. Can run once or on every page load (persistent).

USE THIS when:
- You need to modify page behavior before interacting
- You need to inject helper functions or utilities
- You need to run code on every page navigation

Note: For most tasks, browser_execute or browser_evaluate are simpler. Use this only when you need persistent script injection.`,
          inputSchema: {
            type: 'object',
            properties: {
              code: {
                type: 'string',
                description: 'JavaScript code to inject into the page'
              },
              runOnNewDocument: {
                type: 'boolean',
                description: 'If true, script runs on every page load. If false, runs once on current page.'
              }
            },
            required: ['code']
          }
        },
        {
          name: 'browser_install_extension',
          description: `Automatically install a Chrome extension from Chrome Web Store. Navigates to extensions page, enables developer mode, and installs the extension.

USE THIS when:
- User wants to install a Chrome extension
- You need an extension for a workflow (e.g., 1Password for password management)
- User provides a Chrome Web Store URL

This is a specialized tool - use browser_execute for most browser automation tasks.`,
          inputSchema: {
            type: 'object',
            properties: {
              webStoreUrl: {
                type: 'string',
                description: 'Full URL to the Chrome Web Store extension page. Example: https://chrome.google.com/webstore/detail/1password/aeblfdkhhhdcdjpifhhbdiojplfjncoa'
              }
            },
            required: ['webStoreUrl']
          }
        }
      ];

      return { tools };
    });

    // Execute tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        if (name === 'browser_execute') {
          return await this.executeBrowserTask(args as unknown as ExecuteTaskArgs);
        }

        if (name === 'browser_state') {
          return await this.manageBrowserState(args as unknown as StateManagementArgs);
        }

        if (name === 'browser_generate_script') {
          return await this.generateScript(args as { description: string });
        }

        if (name === 'browser_inspect') {
          return await this.inspectElement(args as { selector: string });
        }

        if (name === 'browser_evaluate') {
          return await this.evaluateCode(args as { code: string; args?: any[] });
        }

        if (name === 'browser_inject_script') {
          return await this.injectScript(args as { code: string; runOnNewDocument?: boolean });
        }

        if (name === 'browser_install_extension') {
          return await this.installExtension(args as { webStoreUrl: string });
        }

        throw new Error(`Unknown tool: ${name}`);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                success: false,
                error: errorMessage
              }, null, 2)
            }
          ],
          isError: true
        };
      }
    });
  }

  /**
   * Execute browser automation task
   */
  private async executeBrowserTask(args: ExecuteTaskArgs): Promise<any> {
    const { task, context, url, waitFor, extract, screenshot } = args;
    const startTime = Date.now();

    try {
      // Validate task is not empty
      if (!task || task.trim().length === 0) {
        throw new Error('Task cannot be empty');
      }

      // Parse natural language task
      // Inject context into the task description if provided
      const taskWithContext = context ? `Context: ${context}\nTask: ${task}` : task;
      const intent = this.intentParser.parseTask(taskWithContext);

      console.error(`🎯 Parsed intent: ${intent.type} (confidence: ${intent.confidence})`);
      console.error(`📋 Actions: ${intent.actions.length}`);

      // Check for suggestions
      const suggestions = this.intentParser.suggestImprovements(task, intent);
      if (suggestions.length > 0) {
        console.error('💡 Suggestions:', suggestions.join(', '));
      }

      // Navigate to URL if provided
      if (url) {
        await this.browserAgent.navigate(url);
      }

      // Execute all parsed actions
      for (const action of intent.actions) {
        await this.browserAgent.executeAction(action);
        console.error(`✅ Executed: ${action.type}`);
      }

      // Wait for selector if specified
      if (waitFor) {
        await this.browserAgent.executeAction({
          type: 'waitForSelector',
          selector: waitFor
        });
      }

      // Extract data if requested
      let extractedData = {};
      if (extract && extract.length > 0) {
        extractedData = await this.browserAgent.extractData(extract);
      }

      // Take screenshot if requested
      let screenshotData;
      if (screenshot) {
        screenshotData = await this.browserAgent.screenshot();
      }

      // State is saved automatically via debounced scheduling in executeAction
      // Only flush to ensure it's saved before returning
      await this.browserAgent.flushStateSave();

      const currentUrl = await this.browserAgent.getCurrentUrl();
      const pageTitle = await this.browserAgent.getPageTitle().catch(() => undefined);
      const executionTimeMs = Date.now() - startTime;

      const result: TaskResult = {
        success: true,
        message: `Completed: ${task}`,
        data: Object.keys(extractedData).length > 0 ? extractedData : undefined,
        currentUrl,
        pageTitle,
        screenshot: screenshotData,
        executionTimeMs
      };

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2)
          }
        ]
      };
    } catch (error) {
      // Still save state on error to preserve progress (force save)
      await this.browserAgent.flushStateSave();

      const errorMessage = error instanceof Error ? error.message : String(error);
      const currentUrl = await this.browserAgent.getCurrentUrl().catch(() => 'unknown');
      const executionTimeMs = Date.now() - startTime;

      const result: TaskResult = {
        success: false,
        message: `Failed: ${task}`,
        error: errorMessage,
        currentUrl,
        executionTimeMs
      };

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2)
          }
        ],
        isError: true
      };
    }
  }

  /**
   * Manage browser state
   */
  private async manageBrowserState(args: StateManagementArgs): Promise<any> {
    const { action } = args;

    try {
      let result: any;

      switch (action) {
        case 'save':
          await this.browserAgent.flushStateSave();
          result = { success: true, message: 'Browser state saved' };
          break;

        case 'clear':
          await this.browserAgent.clearState();
          result = { success: true, message: 'Browser state cleared' };
          break;

        case 'status':
          const hasState = await this.browserAgent.hasState();
          const currentUrl = await this.browserAgent.getCurrentUrl().catch(() => null);
          result = {
            success: true,
            hasPersistedState: hasState,
            currentUrl
          };
          break;

        default:
          throw new Error(`Unknown action: ${action}`);
      }

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2)
          }
        ]
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: errorMessage
            }, null, 2)
          }
        ],
        isError: true
      };
    }
  }

  /**
   * Generate Playwright script from natural language using AI
   */
  private async generateScript(args: { description: string }): Promise<any> {
    if (!this.browserAgent.isLLMEnabled()) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: 'LLM service not configured. Set LLM_TYPE, LLM_BASE_URL, and LLM_MODEL environment variables.'
            }, null, 2)
          }
        ],
        isError: true
      };
    }

    try {
      const result = await this.browserAgent.executeTaskWithAIScript(args.description);
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: 'Script generated and executed successfully',
              result
            }, null, 2)
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error instanceof Error ? error.message : String(error)
            }, null, 2)
          }
        ],
        isError: true
      };
    }
  }

  /**
   * Inspect DOM element
   */
  private async inspectElement(args: { selector: string }): Promise<any> {
    try {
      await this.browserAgent.initialize();
      const page = await this.browserAgent.getPage();
      const inspection = await this.browserAgent.inspectElement(page, args.selector);

      if (!inspection) {
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                success: false,
                error: `Element not found: ${args.selector}`
              }, null, 2)
            }
          ],
          isError: true
        };
      }

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: true,
              inspection
            }, null, 2)
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error instanceof Error ? error.message : String(error)
            }, null, 2)
          }
        ],
        isError: true
      };
    }
  }

  /**
   * Execute JavaScript code in browser context
   */
  private async evaluateCode(args: { code: string; args?: any[] }): Promise<any> {
    try {
      await this.browserAgent.initialize();
      const page = await this.browserAgent.getPage();
      const result = await this.browserAgent.evaluateCode(page, args.code, args.args);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: true,
              result
            }, null, 2)
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error instanceof Error ? error.message : String(error)
            }, null, 2)
          }
        ],
        isError: true
      };
    }
  }

  /**
   * Inject script into page
   */
  private async injectScript(args: { code: string; runOnNewDocument?: boolean }): Promise<any> {
    try {
      await this.browserAgent.initialize();
      const page = await this.browserAgent.getPage();
      await this.browserAgent.injectScript(page, args.code, args.runOnNewDocument || false);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: true,
              message: `Script injected${args.runOnNewDocument ? ' (persistent)' : ''}`
            }, null, 2)
          }
        ]
      };
    } catch (error) {
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: error instanceof Error ? error.message : String(error)
            }, null, 2)
          }
        ],
        isError: true
      };
    }
  }

  /**
   * Install extension from Chrome Web Store
   */
  private async installExtension(args: { webStoreUrl: string }): Promise<any> {
    const { webStoreUrl } = args;

    try {
      // Validate URL
      if (!webStoreUrl || !webStoreUrl.includes('chrome.google.com/webstore')) {
        throw new Error('Invalid Chrome Web Store URL. Must be a chrome.google.com/webstore URL.');
      }

      const result = await this.browserAgent.installExtensionFromWebStore(webStoreUrl);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(result, null, 2)
          }
        ],
        isError: !result.success
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              success: false,
              error: errorMessage
            }, null, 2)
          }
        ],
        isError: true
      };
    }
  }
}
