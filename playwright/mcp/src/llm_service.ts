/**
 * LLM Service for AI Script Generation
 * Supports LLM Studio, Local APIs, Ollama, and OpenAI
 */

import OpenAI from 'openai';

export interface LLMConfig {
  type: 'llm-studio' | 'local-api' | 'ollama' | 'openai' | 'disabled';
  baseURL?: string;
  apiKey?: string;
  model?: string;
}

export interface GeneratedScript {
  code: string;
  explanation: string;
  selectors: string[];
  estimatedTime: string;
}

export class LLMService {
  private client: OpenAI | null = null;
  private config: LLMConfig;
  private enabled: boolean = false;

  constructor(config: LLMConfig) {
    this.config = config;
    if (config.type !== 'disabled') {
      this.initialize();
    }
  }

  private initialize() {
    try {
      const baseURL = this.getBaseURL();
      const apiKey = this.config.apiKey || 'not-needed'; // Local LLMs often don't need real keys

      this.client = new OpenAI({
        baseURL,
        apiKey,
      });

      this.enabled = true;
      console.error(`✅ LLM Service initialized: ${this.config.type} at ${baseURL}`);
    } catch (error) {
      console.error(`⚠️  LLM Service initialization failed: ${error}`);
      this.enabled = false;
    }
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

  isEnabled(): boolean {
    return this.enabled && this.client !== null;
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
  ): Promise<GeneratedScript> {
    if (!this.isEnabled()) {
      throw new Error('LLM service not enabled or initialized');
    }

    const prompt = this.buildScriptGenerationPrompt(description, context);

    try {
      const response = await this.client!.chat.completions.create({
        model: this.config.model || 'gpt-3.5-turbo',
        messages: [
          {
            role: 'system',
            content: `You are an expert Playwright automation engineer. Generate TypeScript Playwright code that is:
- Correct and executable
- Uses Playwright's Locator API (getByRole, getByText, getByLabel, etc.)
- Includes proper error handling
- Uses smart waits (waitForLoadState, waitForSelector)
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
        temperature: 0.3,
        max_tokens: 2000,
        response_format: { type: 'json_object' }
      });

      const content = response.choices[0]?.message?.content;
      if (!content) {
        throw new Error('No response from LLM');
      }

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
    if (!this.isEnabled()) {
      throw new Error('LLM service not enabled or initialized');
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
      const response = await this.client!.chat.completions.create({
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
1. Uses Playwright's Locator API (getByRole, getByText, getByLabel, etc.)
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

