/**
 * Browser Key Fetcher Utility
 *
 * Generates intelligent browser automation commands to fetch API keys
 * Uses Playwright MCP server (sole browser automation tool)
 */

import { KeyStatus } from './key_detector.js';

export interface BrowserStep {
  action: 'navigate' | 'click' | 'type' | 'wait' | 'copy' | 'check';
  selector?: string;
  text?: string;
  description: string;
  manualStep?: string; // Manual instruction if automation fails
}

export interface KeyFetchCommand {
  provider: string;
  priority: number;
  url: string;
  steps: BrowserStep[];
  manualInstructions: string[];
  playwrightCommands: string[]; // Commands for Playwright MCP (sole browser automation tool)
}

export class BrowserKeyFetcher {
  /**
   * Generate browser commands for Hugging Face
   */
  static generateHuggingFaceCommands(): KeyFetchCommand {
    return {
      provider: 'Hugging Face',
      priority: 1,
      url: 'https://huggingface.co/settings/tokens',
      steps: [
        {
          action: 'navigate',
          description: 'Navigate to Hugging Face token settings',
          manualStep: 'Open https://huggingface.co/settings/tokens in your browser'
        },
        {
          action: 'check',
          selector: 'body',
          description: 'Check if logged in (look for login button or token list)',
          manualStep: 'If not logged in, click "Sign in" and log in with your account'
        },
        {
          action: 'click',
          selector: 'button:has-text("New token"), a:has-text("New token"), [data-testid="new-token-button"]',
          description: 'Click "New token" button',
          manualStep: 'Click the "New token" or "+" button to create a new token'
        },
        {
          action: 'type',
          selector: 'input[name="name"], input[placeholder*="name"], input[type="text"]',
          text: 'Image-Video-MCP',
          description: 'Enter token name',
          manualStep: 'Enter a name like "Image-Video-MCP" for the token'
        },
        {
          action: 'click',
          selector: 'button:has-text("Generate"), button[type="submit"]',
          description: 'Click generate button',
          manualStep: 'Click "Generate token" or "Create" button'
        },
        {
          action: 'copy',
          selector: 'code, [data-testid="token-value"], input[readonly]',
          description: 'Copy the generated token',
          manualStep: 'Copy the token value (it will only be shown once!)'
        }
      ],
      manualInstructions: [
        '1. Go to https://huggingface.co/settings/tokens',
        '2. Log in if needed',
        '3. Click "New token" or "+" button',
        '4. Enter name: "Image-Video-MCP"',
        '5. Select "Read" permission (or "Write" if needed)',
        '6. Click "Generate token"',
        '7. Copy the token immediately (it won\'t be shown again)',
        '8. Add to .env file: HUGGINGFACE_API_KEY=your_token_here'
      ],
      playwrightCommands: [
        'goto https://huggingface.co/settings/tokens',
        'waitForLoadState networkidle',
        'click text="New token"',
        'fill input[name="name"] Image-Video-MCP',
        'click button:has-text("Generate")',
        'copy text from code element'
      ]
    };
  }

  /**
   * Generate browser commands for Replicate
   */
  static generateReplicateCommands(): KeyFetchCommand {
    return {
      provider: 'Replicate',
      priority: 2,
      url: 'https://replicate.com/account/api-tokens',
      steps: [
        {
          action: 'navigate',
          description: 'Navigate to Replicate API tokens page',
          manualStep: 'Open https://replicate.com/account/api-tokens in your browser'
        },
        {
          action: 'check',
          selector: 'body',
          description: 'Check if logged in',
          manualStep: 'If not logged in, click "Sign in" and log in'
        },
        {
          action: 'click',
          selector: 'button:has-text("Create token"), a:has-text("Create"), button[aria-label*="Create"]',
          description: 'Click create token button',
          manualStep: 'Click "Create token" or "+" button'
        },
        {
          action: 'type',
          selector: 'input[name="name"], input[placeholder*="name"]',
          text: 'Image-Video-MCP',
          description: 'Enter token name',
          manualStep: 'Enter a name like "Image-Video-MCP"'
        },
        {
          action: 'click',
          selector: 'button:has-text("Create"), button[type="submit"]',
          description: 'Click create button',
          manualStep: 'Click "Create" button'
        },
        {
          action: 'copy',
          selector: 'code, [data-testid="token"], input[readonly]',
          description: 'Copy the generated token',
          manualStep: 'Copy the token value (starts with r8_)'
        }
      ],
      manualInstructions: [
        '1. Go to https://replicate.com/account/api-tokens',
        '2. Log in if needed',
        '3. Click "Create token" or "+" button',
        '4. Enter name: "Image-Video-MCP"',
        '5. Click "Create"',
        '6. Copy the token (starts with r8_)',
        '7. Add to .env file: REPLICATE_API_TOKEN=your_token_here'
      ],
      playwrightCommands: [
        'goto https://replicate.com/account/api-tokens',
        'waitForLoadState networkidle',
        'click text="Create token"',
        'fill input[name="name"] Image-Video-MCP',
        'click button:has-text("Create")',
        'copy text from code element'
      ]
    };
  }

  /**
   * Generate browser commands for Fal.ai
   */
  static generateFalCommands(): KeyFetchCommand {
    return {
      provider: 'Fal.ai',
      priority: 3,
      url: 'https://fal.ai/dashboard/keys',
      steps: [
        {
          action: 'navigate',
          description: 'Navigate to Fal.ai dashboard keys',
          manualStep: 'Open https://fal.ai/dashboard/keys in your browser'
        },
        {
          action: 'check',
          selector: 'body',
          description: 'Check if logged in',
          manualStep: 'If not logged in, click "Sign in" and log in'
        },
        {
          action: 'click',
          selector: 'button:has-text("Create"), button:has-text("New"), a:has-text("Create key")',
          description: 'Click create key button',
          manualStep: 'Click "Create key" or "+" button'
        },
        {
          action: 'type',
          selector: 'input[name="name"], input[placeholder*="name"]',
          text: 'Image-Video-MCP',
          description: 'Enter key name',
          manualStep: 'Enter a name like "Image-Video-MCP"'
        },
        {
          action: 'click',
          selector: 'button:has-text("Create"), button[type="submit"]',
          description: 'Click create button',
          manualStep: 'Click "Create" button'
        },
        {
          action: 'copy',
          selector: 'code, [data-testid="key"], input[readonly]',
          description: 'Copy the generated API key',
          manualStep: 'Copy the API key value'
        }
      ],
      manualInstructions: [
        '1. Go to https://fal.ai/dashboard/keys',
        '2. Log in if needed',
        '3. Click "Create key" or "+" button',
        '4. Enter name: "Image-Video-MCP"',
        '5. Click "Create"',
        '6. Copy the API key',
        '7. Add to .env file: FAL_API_KEY=your_key_here'
      ],
      playwrightCommands: [
        'goto https://fal.ai/dashboard/keys',
        'waitForLoadState networkidle',
        'click text="Create"',
        'fill input[name="name"] Image-Video-MCP',
        'click button:has-text("Create")',
        'copy text from code element'
      ]
    };
  }

  /**
   * Generate browser commands for OpenAI
   */
  static generateOpenAICommands(): KeyFetchCommand {
    return {
      provider: 'OpenAI',
      priority: 4,
      url: 'https://platform.openai.com/api-keys',
      steps: [
        {
          action: 'navigate',
          description: 'Navigate to OpenAI API keys page',
          manualStep: 'Open https://platform.openai.com/api-keys in your browser'
        },
        {
          action: 'check',
          selector: 'body',
          description: 'Check if logged in',
          manualStep: 'If not logged in, click "Sign in" and log in'
        },
        {
          action: 'click',
          selector: 'button:has-text("Create new secret key"), a:has-text("Create"), button[aria-label*="Create"]',
          description: 'Click create new secret key button',
          manualStep: 'Click "Create new secret key" or "+" button'
        },
        {
          action: 'type',
          selector: 'input[name="name"], input[placeholder*="name"]',
          text: 'Image-Video-MCP',
          description: 'Enter key name',
          manualStep: 'Enter a name like "Image-Video-MCP"'
        },
        {
          action: 'click',
          selector: 'button:has-text("Create"), button[type="submit"]',
          description: 'Click create button',
          manualStep: 'Click "Create secret key" button'
        },
        {
          action: 'copy',
          selector: 'code, [data-testid="key"], input[readonly]',
          description: 'Copy the generated key',
          manualStep: 'Copy the key value (starts with sk-)'
        }
      ],
      manualInstructions: [
        '1. Go to https://platform.openai.com/api-keys',
        '2. Log in if needed',
        '3. Click "Create new secret key" or "+" button',
        '4. Enter name: "Image-Video-MCP"',
        '5. Click "Create secret key"',
        '6. Copy the key (starts with sk-)',
        '7. Add to .env file: OPENAI_API_KEY=your_key_here'
      ],
      playwrightCommands: [
        'goto https://platform.openai.com/api-keys',
        'waitForLoadState networkidle',
        'click text="Create new secret key"',
        'fill input[name="name"] Image-Video-MCP',
        'click button:has-text("Create")',
        'copy text from code element'
      ]
    };
  }

  /**
   * Generate commands for all missing keys
   */
  static generateCommandsForMissingKeys(missingKeys: KeyStatus[]): KeyFetchCommand[] {
    const commands: KeyFetchCommand[] = [];

    for (const key of missingKeys) {
      switch (key.key) {
        case 'HUGGINGFACE_API_KEY':
          commands.push(this.generateHuggingFaceCommands());
          break;
        case 'REPLICATE_API_TOKEN':
          commands.push(this.generateReplicateCommands());
          break;
        case 'FAL_API_KEY':
          commands.push(this.generateFalCommands());
          break;
        case 'OPENAI_API_KEY':
          commands.push(this.generateOpenAICommands());
          break;
      }
    }

    return commands.sort((a, b) => a.priority - b.priority);
  }

  /**
   * Generate MCP command list for Playwright (sole browser automation tool)
   */
  static generatePlaywrightMCPCommands(commands: KeyFetchCommand[]): string[] {
    const mcpCommands: string[] = [];

    for (const cmd of commands) {
      mcpCommands.push(`# ${cmd.provider} API Key Fetch`);
      mcpCommands.push(`# Priority: ${cmd.priority} - ${cmd.description || ''}`);
      mcpCommands.push(`# URL: ${cmd.url}`);
      mcpCommands.push('');
      mcpCommands.push(...cmd.playwrightCommands);
      mcpCommands.push('');
    }

    return mcpCommands;
  }

  /**
   * Generate formatted instructions
   */
  static formatInstructions(commands: KeyFetchCommand[]): string {
    let output = '='.repeat(60) + '\n';
    output += 'API Key Setup Instructions\n';
    output += '='.repeat(60) + '\n\n';

    for (const cmd of commands) {
      output += `\n${cmd.provider} (Priority ${cmd.priority})\n`;
      output += '-'.repeat(60) + '\n';
      output += `URL: ${cmd.url}\n\n`;
      output += 'Manual Steps:\n';
      cmd.manualInstructions.forEach((step, i) => {
        output += `  ${step}\n`;
      });
      output += '\n';
    }

    return output;
  }
}


