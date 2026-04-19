/**
 * Type definitions for Playwright MCP Server
 */

export interface BrowserAction {
  type: 'click' | 'fill' | 'select' | 'wait' | 'waitForSelector' | 'navigate' | 'screenshot' | 'keyPress' | 'evaluate' | 'inspect' | 'injectScript';
  selector?: string;
  value?: string;
  duration?: number;
  url?: string;
  path?: string;
  key?: string;
  // Locator API support
  locatorType?: 'role' | 'text' | 'label' | 'placeholder' | 'testid' | 'css';
  locatorText?: string;
  // Code injection support
  code?: string; // JavaScript code to execute
  args?: any[]; // Arguments to pass to code
  runOnNewDocument?: boolean; // For injectScript: run on every page load
}

export interface TimeoutConfig {
  navigation?: number;
  action?: number;
  element?: number;
  visibility?: number;
}

export interface TaskIntent {
  type: string;
  confidence: number;
  actions: BrowserAction[];
  description: string;
}

export interface ExecuteTaskArgs {
  task: string;
  context?: string;
  url?: string;
  waitFor?: string;
  extract?: string[];
  screenshot?: boolean;
}

export interface StateManagementArgs {
  action: 'save' | 'restore' | 'clear' | 'status';
  stateKey?: string;
}

export interface ExtractedData {
  [selector: string]: string[] | null;
}

export interface TaskResult {
  success: boolean;
  message: string;
  data?: ExtractedData;
  currentUrl?: string;
  pageTitle?: string;
  screenshot?: string;
  error?: string;
  executionTimeMs?: number;
}
