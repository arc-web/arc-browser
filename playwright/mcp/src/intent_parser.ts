/**
 * Natural Language Intent Parser
 * Converts natural language to Playwright actions using Locator API
 */

import type { BrowserAction, TaskIntent } from './types.js';

export class IntentParser {
  /**
   * Parse natural language task to executable intent
   */
  parseTask(task: string): TaskIntent {
    // Handle very long task strings
    if (task.length > 1000) {
      console.error('⚠️  Task string very long, truncating...');
      task = task.substring(0, 1000);
    }

    const taskLower = task.toLowerCase();
    const actions: BrowserAction[] = [];
    let type = 'unknown';
    let confidence = 0.5;

    // Check for multi-step commands (comma-separated)
    if (task.includes(',') && (task.match(/,/g) || []).length >= 1) {
      // Split by commas and parse each part
      const parts = task.split(',').map(s => s.trim()).filter(s => s.length > 0);
      const allActions: BrowserAction[] = [];

      for (const part of parts) {
        const partIntent = this.parseTask(part);
        allActions.push(...partIntent.actions);
      }

      return {
        type: 'multi_step',
        confidence: 0.85,
        actions: allActions,
        description: task
      };
    }

    // Navigate detection
    if (taskLower.includes('go to') || taskLower.includes('navigate') || taskLower.includes('visit')) {
      const url = this.extractUrl(task);
      if (url) {
        actions.push({ type: 'navigate', url });
        type = 'navigation';
        confidence = 0.95;
      }
    }

    // Click detection - FIXED: Use Locator API with escaped special chars
    const clickMatch = taskLower.match(/click(?:\s+(?:on|the))?\s+["']?([^"']+)["']?/);
    if (clickMatch) {
      let buttonText = clickMatch[1].trim();
      // Escape special regex characters for better matching
      // Note: Playwright's getByRole/getByText handles this, but we keep original for display
      actions.push({
        type: 'click',
        locatorType: 'role', // Use role-based finding (most reliable)
        locatorText: buttonText,
        selector: buttonText // Fallback
      });
      type = 'interaction';
      confidence = 0.90;
    }

    // Fill/Enter detection - FIXED: Use Locator API
    const fillMatch = taskLower.match(/(?:fill|enter|type)(?:\s+in)?\s+["']?([^"']+)["']?\s+(?:with|as)?\s*["']([^"']+)["']?/);
    if (fillMatch) {
      const fieldName = fillMatch[1].trim();
      const value = fillMatch[2].trim();
      actions.push({
        type: 'fill',
        locatorType: 'label', // Try label first, then placeholder
        locatorText: fieldName,
        selector: fieldName, // Fallback
        value
      });
      type = 'form_fill';
      confidence = 0.88;
    }

    // Select detection
    const selectMatch = taskLower.match(/select\s+["']?([^"']+)["']?/);
    if (selectMatch) {
      const option = selectMatch[1].trim();
      actions.push({
        type: 'select',
        selector: 'select',
        value: option
      });
      type = 'selection';
      confidence = 0.85;
    }

    // Wait detection
    const waitMatch = taskLower.match(/wait\s+(?:for\s+)?(\d+)?\s*(?:seconds?|ms)?/);
    if (waitMatch) {
      const duration = waitMatch[1] ? parseInt(waitMatch[1]) * 1000 : 1000;
      actions.push({
        type: 'wait',
        duration
      });
      type = 'wait';
      confidence = 0.95;
    }

    // Screenshot detection
    if (taskLower.includes('screenshot') || taskLower.includes('capture')) {
      actions.push({ type: 'screenshot' });
      type = 'screenshot';
      confidence = 0.95;
    }

    // Enter key press detection
    if (taskLower.includes('press enter') || taskLower.includes('hit enter') ||
        taskLower.includes('submit form') || taskLower.includes('press return')) {
      actions.push({ type: 'keyPress', key: 'Enter' });
      type = 'key_press';
      confidence = 0.90;
    }

    // Text extraction detection ("tell me", "extract", "get text")
    if (taskLower.match(/(?:tell me|extract|get|show|what is|what's).*(?:text|heading|title|content)/)) {
      // Extract selector if specified, otherwise default to common selectors
      const selectorMatch = taskLower.match(/(?:from|of|the)\s+["']?([^"']+)["']?/);
      if (selectorMatch) {
        // User specified a selector
        type = 'extraction';
        confidence = 0.85;
      } else if (taskLower.includes('heading') || taskLower.includes('h1') || taskLower.includes('h2') || taskLower.includes('h3')) {
        // Default to headings if mentioned
        type = 'extraction';
        confidence = 0.80;
      }
    }

    return {
      type,
      confidence,
      actions,
      description: task
    };
  }

  /**
   * Extract URL from text - FIXED: Validates URL format
   */
  private extractUrl(text: string): string | null {
    const urlMatch = text.match(/https?:\/\/[^\s]+/);
    if (urlMatch) {
      try {
        // Validate URL format
        new URL(urlMatch[0]);
        return urlMatch[0];
      } catch {
        // Invalid URL format
        return null;
      }
    }

    // Try to extract domain and construct URL
    const domainMatch = text.match(/(?:go to|visit|navigate to)\s+([a-z0-9.-]+\.[a-z]{2,})/i);
    if (domainMatch) {
      const constructedUrl = `https://${domainMatch[1]}`;
      try {
        // Validate constructed URL
        new URL(constructedUrl);
        return constructedUrl;
      } catch {
        return null;
      }
    }

    return null;
  }

  /**
   * Extract quoted text
   */
  private extractQuoted(text: string): string | null {
    const match = text.match(/"([^"]+)"|'([^']+)'/);
    return match ? (match[1] || match[2]) : null;
  }

  /**
   * Suggest improvements for unclear tasks
   */
  suggestImprovements(task: string, intent: TaskIntent): string[] {
    const suggestions: string[] = [];

    if (intent.confidence < 0.7) {
      suggestions.push('Task unclear. Try being more specific about the action.');
    }

    if (intent.actions.length === 0) {
      suggestions.push('No actions detected. Include verbs like "click", "fill", "navigate", or "select".');
    }

    if (task.toLowerCase().includes('click') && !task.includes('"') && !task.includes("'")) {
      suggestions.push('Put button/link text in quotes for better accuracy.');
    }

    return suggestions;
  }
}
