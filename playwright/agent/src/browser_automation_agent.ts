/**
 * Browser Automation Agent
 *
 * Autonomous agent that executes browser-based tasks with real-time feedback.
 * Wraps Playwright automation with intelligent task interpretation and
 * intuitive insight generation.
 */

import { EventEmitter } from 'events';
import { chromium, Browser, Page, BrowserContext } from 'playwright';
import * as fs from 'fs/promises';
import * as path from 'path';
import type {
  AgentTask,
  AgentStatus,
  AgentInsight,
  TaskResult,
  ExecutionContext
} from './types';

export class browser_automation_agent extends EventEmitter {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private currentTask: AgentTask | null = null;
  private executionContext: ExecutionContext;

  // Add state persistence
  private readonly storageStatePath: string;
  private readonly stateDir: string;

  public readonly agentId: string;
  public readonly name: string = 'Browser Automation Agent';
  public readonly capabilities: string[] = [
    'navigate_web_pages',
    'fill_forms',
    'click_elements',
    'extract_data',
    'handle_auth_flows',
    'verify_visual_state',
    'slack_oauth_setup',
    'web_form_automation',
    'persistent_sessions'
  ];

  constructor(agentId: string = 'browser_agent-001', stateDir?: string) {
    super();
    this.agentId = agentId;

    // Setup persistent state storage
    this.stateDir = stateDir || path.join(__dirname, '.browser-state');
    this.storageStatePath = path.join(this.stateDir, `${agentId}-state.json`);

    this.executionContext = {
      startTime: null,
      taskHistory: [],
      insights: [],
      metrics: {
        tasksCompleted: 0,
        tasksFailed: 0,
        averageExecutionTime: 0,
        successRate: 0
      }
    };
  }

  /**
   * Execute a task with real-time feedback AND persistent state
   */
  async executeTask(task: AgentTask): Promise<TaskResult> {
    this.currentTask = task;
    this.executionContext.startTime = Date.now();

    try {
      // Emit status: Starting
      this.emitStatus({
        stage: 'starting',
        message: `🤖 Starting task: ${task.description}`,
        taskId: task.id,
        timestamp: new Date().toISOString()
      });

      // Parse task intent
      const intent = this.parseIntent(task);

      this.emitInsight({
        type: 'task_analysis',
        message: `💡 Detected task type: ${intent.type}`,
        confidence: intent.confidence,
        timestamp: new Date().toISOString()
      });

      // Initialize browser with persistent state
      await this.initializeBrowser(task.browserOptions);

      // Execute based on intent
      let result: TaskResult;

      switch (intent.type) {
        case 'slack_oauth_setup':
          result = await this.executeSlackOAuthSetup(intent.params);
          break;

        case 'web_form_automation':
          result = await this.executeWebFormAutomation(intent.params);
          break;

        case 'data_extraction':
          result = await this.executeDataExtraction(intent.params);
          break;

        default:
          throw new Error(`Unknown task type: ${intent.type}`);
      }

      // CRITICAL: Save browser state after successful task
      await this.saveState();

      // Emit completion status
      this.emitStatus({
        stage: 'completed',
        message: '🎉 Task completed successfully!',
        taskId: task.id,
        timestamp: new Date().toISOString()
      });

      // Update metrics
      this.updateMetrics(result);

      return result;

    } catch (error) {
      // Save state even on error to preserve progress
      await this.saveState();

      const errorMessage = error instanceof Error ? error.message : String(error);

      this.emitStatus({
        stage: 'error',
        message: `❌ Task failed: ${errorMessage}`,
        taskId: task.id,
        error: error,
        timestamp: new Date().toISOString()
      });

      return {
        success: false,
        error: errorMessage,
        taskId: task.id,
        executionTime: Date.now() - this.executionContext.startTime!
      };
    }
  }

  /**
   * Initialize Playwright browser WITH persistent state
   */
  private async initializeBrowser(options?: any): Promise<void> {
    // Only launch browser once
    if (!this.browser) {
      this.emitStatus({
        stage: 'initialization',
        message: '🌐 Launching browser...',
        timestamp: new Date().toISOString()
      });

      this.browser = await chromium.launch({
        headless: options?.headless ?? false,
        slowMo: options?.slowMo ?? 100,
        timeout: 0 // Keep browser alive
      });
    }

    // Only create context once, loading saved state
    if (!this.context) {
      this.emitStatus({
        stage: 'initialization',
        message: '🔄 Loading browser state...',
        timestamp: new Date().toISOString()
      });

      // Load existing storage state if available
      let storageState = undefined;
      try {
        await fs.access(this.storageStatePath);
        storageState = JSON.parse(
          await fs.readFile(this.storageStatePath, 'utf-8')
        );
        this.emitInsight({
          type: 'state_loaded',
          message: '✅ Loaded persistent browser state (cookies, auth, etc.)',
          timestamp: new Date().toISOString()
        });
      } catch (error) {
        this.emitInsight({
          type: 'state_info',
          message: 'ℹ️  No existing state found, starting fresh session',
          timestamp: new Date().toISOString()
        });
      }

      // Create context with loaded state
      this.context = await this.browser.newContext({
        viewport: { width: 1920, height: 1080 },
        storageState, // Apply saved cookies, localStorage, etc.
        ...options?.contextOptions
      });
    }

    // Create page if needed
    if (!this.page) {
      this.page = await this.context.newPage();
    }

    this.emitInsight({
      type: 'initialization',
      message: '✅ Browser ready for automation',
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Save browser state to disk
   */
  private async saveState(): Promise<void> {
    if (!this.context) return;

    try {
      // Extract all browser state (cookies, localStorage, sessionStorage, etc.)
      const state = await this.context.storageState();

      // Ensure directory exists
      await fs.mkdir(this.stateDir, { recursive: true });

      // Save to file
      await fs.writeFile(
        this.storageStatePath,
        JSON.stringify(state, null, 2)
      );

      this.emitInsight({
        type: 'state_saved',
        message: '💾 Browser state saved (authentication and session preserved)',
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      console.error('❌ Failed to save browser state:', error);
    }
  }

  /**
   * Clear saved browser state (logout/reset)
   */
  async clearState(): Promise<void> {
    try {
      await fs.unlink(this.storageStatePath);
      this.emitInsight({
        type: 'state_cleared',
        message: '🗑️  Browser state cleared',
        timestamp: new Date().toISOString()
      });
    } catch (error) {
      // File might not exist, that's ok
    }
  }

  /**
   * Parse natural language or structured task into executable intent
   */
  private parseIntent(task: AgentTask): { type: string; confidence: number; params: any } {
    const description = task.description.toLowerCase();

    // Slack OAuth detection
    if (description.includes('slack') && (description.includes('oauth') || description.includes('scope'))) {
      return {
        type: 'slack_oauth_setup',
        confidence: 0.95,
        params: {
          appId: task.params?.appId || process.env.SLACK_APP_ID,
          scopes: task.params?.scopes || [
            'channels:history',
            'channels:read',
            'chat:write',
            'reactions:write',
            'users:read',
            'users.profile:read'
          ]
        }
      };
    }

    // Web form detection
    if (description.includes('form') || description.includes('fill')) {
      return {
        type: 'web_form_automation',
        confidence: 0.85,
        params: task.params
      };
    }

    // Data extraction detection
    if (description.includes('extract') || description.includes('scrape') || description.includes('data')) {
      return {
        type: 'data_extraction',
        confidence: 0.80,
        params: task.params
      };
    }

    return {
      type: 'unknown',
      confidence: 0.0,
      params: task.params
    };
  }

  /**
   * Execute Slack OAuth setup - wraps the Playwright script
   */
  private async executeSlackOAuthSetup(params: any): Promise<TaskResult> {
    const { appId, scopes } = params;
    const startTime = Date.now();

    this.emitStatus({
      stage: 'navigation',
      message: `🌐 Navigating to Slack app ${appId}...`,
      timestamp: new Date().toISOString()
    });

    // Navigate to OAuth page
    const oauthUrl = `https://api.slack.com/apps/${appId}/oauth?`;
    await this.page!.goto(oauthUrl, { waitUntil: 'networkidle' });

    this.emitInsight({
      type: 'page_analysis',
      message: '💡 OAuth page loaded - analyzing current scopes...',
      timestamp: new Date().toISOString()
    });

    // Check existing scopes
    const existingScopes = await this.getCurrentScopes();
    const scopesToAdd = scopes.filter((scope: string) => !existingScopes.includes(scope));

    this.emitInsight({
      type: 'scope_analysis',
      message: `📊 Found ${existingScopes.length}/6 scopes configured. Need to add ${scopesToAdd.length} more.`,
      data: {
        existing: existingScopes,
        toAdd: scopesToAdd
      },
      timestamp: new Date().toISOString()
    });

    // Add each scope with real-time feedback
    for (let i = 0; i < scopesToAdd.length; i++) {
      const scope = scopesToAdd[i];

      this.emitStatus({
        stage: 'scope_addition',
        message: `⏳ Adding scope ${i + 1}/${scopesToAdd.length}: ${scope}`,
        progress: {
          current: i + 1,
          total: scopesToAdd.length,
          percentage: Math.round(((i + 1) / scopesToAdd.length) * 100)
        },
        timestamp: new Date().toISOString()
      });

      const added = await this.addScope(scope);

      if (added) {
        this.emitInsight({
          type: 'scope_added',
          message: `✅ ${scope} - ${this.explainScope(scope)}`,
          timestamp: new Date().toISOString()
        });
      }
    }

    // Final verification
    const finalScopes = await this.getCurrentScopes();
    const allAdded = scopes.every((scope: string) => finalScopes.includes(scope));

    if (allAdded) {
      this.emitInsight({
        type: 'completion',
        message: '🎉 All OAuth scopes configured successfully!',
        data: {
          totalScopes: finalScopes.length,
          configuredScopes: finalScopes
        },
        timestamp: new Date().toISOString()
      });

      this.emitInsight({
        type: 'next_step',
        message: '💡 Next: Install app to workspace to get bot token?',
        actionable: true,
        suggestedAction: 'install_to_workspace',
        timestamp: new Date().toISOString()
      });
    }

    return {
      success: allAdded,
      taskId: this.currentTask!.id,
      executionTime: Date.now() - startTime,
      data: {
        scopesConfigured: finalScopes.length,
        scopes: finalScopes
      }
    };
  }

  /**
   * Get current OAuth scopes from Slack page
   */
  private async getCurrentScopes(): Promise<string[]> {
    // Implementation would query the Slack page for existing scopes
    // This is a simplified version
    const scopeElements = await this.page!.$$('[data-qa="oauth_scope_name"]');
    const scopes: string[] = [];

    for (const element of scopeElements) {
      const text = await element.textContent();
      if (text) scopes.push(text.trim());
    }

    return scopes;
  }

  /**
   * Add a single OAuth scope
   */
  private async addScope(scope: string): Promise<boolean> {
    try {
      // Click "Add an OAuth Scope" button
      await this.page!.click('button:has-text("Add an OAuth Scope")');
      await this.page!.waitForSelector('[role="listbox"]', { timeout: 5000 });

      // Find and click the scope option
      const option = await this.page!.$(`[role="option"]:has-text("${scope}")`);

      if (!option) {
        this.emitInsight({
          type: 'warning',
          message: `⚠️ Scope "${scope}" not found in dropdown`,
          timestamp: new Date().toISOString()
        });
        return false;
      }

      // Handle page reload after selection
      await Promise.all([
        this.page!.waitForNavigation({ waitUntil: 'networkidle', timeout: 10000 }),
        option.click()
      ]);

      await this.page!.waitForTimeout(1000);
      return true;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      this.emitInsight({
        type: 'error',
        message: `❌ Failed to add scope "${scope}": ${errorMessage}`,
        timestamp: new Date().toISOString()
      });
      return false;
    }
  }

  /**
   * Explain what a scope does (for insights)
   */
  private explainScope(scope: string): string {
    const explanations: Record<string, string> = {
      'channels:history': 'Enables reading message history from public channels',
      'channels:read': 'Allows viewing basic channel information',
      'chat:write': 'Enables posting messages as your bot',
      'reactions:write': 'Allows adding emoji reactions to messages',
      'users:read': 'Enables viewing user information in workspace',
      'users.profile:read': 'Allows reading user profile information'
    };

    return explanations[scope] || 'Permission for specific Slack functionality';
  }

  /**
   * Stub for web form automation
   */
  private async executeWebFormAutomation(params: any): Promise<TaskResult> {
    // To be implemented in Phase 2
    throw new Error('Web form automation not yet implemented');
  }

  /**
   * Stub for data extraction
   */
  private async executeDataExtraction(params: any): Promise<TaskResult> {
    // To be implemented in Phase 2
    throw new Error('Data extraction not yet implemented');
  }

  /**
   * Emit status update
   */
  private emitStatus(status: AgentStatus): void {
    this.emit('status', status);
  }

  /**
   * Emit insight
   */
  private emitInsight(insight: AgentInsight): void {
    this.executionContext.insights.push(insight);
    this.emit('insight', insight);
  }

  /**
   * Update execution metrics
   */
  private updateMetrics(result: TaskResult): void {
    if (result.success) {
      this.executionContext.metrics.tasksCompleted++;
    } else {
      this.executionContext.metrics.tasksFailed++;
    }

    const totalTasks = this.executionContext.metrics.tasksCompleted + this.executionContext.metrics.tasksFailed;
    this.executionContext.metrics.successRate = this.executionContext.metrics.tasksCompleted / totalTasks;

    // Update average execution time
    const currentAvg = this.executionContext.metrics.averageExecutionTime;
    this.executionContext.metrics.averageExecutionTime =
      (currentAvg * (totalTasks - 1) + result.executionTime) / totalTasks;
  }

  /**
   * Clean up resources (use sparingly - kills persistent session!)
   * @param fullShutdown - If false, keeps browser alive for next task (default: false)
   */
  async cleanup(fullShutdown: boolean = false): Promise<void> {
    // Always save state before cleanup
    await this.saveState();

    if (fullShutdown) {
      // Full cleanup - end of entire session
      if (this.page) await this.page.close();
      if (this.context) await this.context.close();
      if (this.browser) await this.browser.close();

      this.page = null;
      this.context = null;
      this.browser = null;

      this.emitInsight({
        type: 'cleanup',
        message: '🔌 Browser fully shut down',
        timestamp: new Date().toISOString()
      });
    } else {
      // Soft cleanup - just close page, keep browser/context alive
      if (this.page) {
        await this.page.close();
        this.page = null;
      }

      this.emitInsight({
        type: 'cleanup',
        message: '♻️  Page closed, browser session kept alive',
        timestamp: new Date().toISOString()
      });
    }
  }

  /**
   * Get current execution context
   */
  getContext(): ExecutionContext {
    return { ...this.executionContext };
  }
}
