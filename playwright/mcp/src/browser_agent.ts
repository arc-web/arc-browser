/**
 * Persistent Browser Agent for MCP Server
 * Wraps Playwright with state persistence and intelligent element finding
 */

import { chromium, Browser, BrowserContext, Page, Locator } from 'playwright';
import * as fs from 'fs/promises';
import * as path from 'path';
import { createHash } from 'crypto';
import type { BrowserAction, ExtractedData, TimeoutConfig } from './types.js';
import { LLMService, LLMConfig, GeneratedScript } from './llm_service.js';

export class PersistentBrowserAgent {
  private browser: Browser | null = null;
  private context: BrowserContext | null = null;
  private page: Page | null = null;
  private currentUrl: string | null = null;

  // Action queue to prevent concurrent actions
  private actionQueue: Promise<void> = Promise.resolve();
  private isExecuting: boolean = false;

  // State persistence optimization
  private stateSaveTimer: NodeJS.Timeout | null = null;
  private lastStateHash: string = '';
  private pendingStateSave: Promise<void> | null = null;
  private readonly STATE_SAVE_DEBOUNCE_MS = 1000; // Save 1 second after last action
  private readonly FORCE_SAVE_ACTIONS = ['navigate', 'fill']; // Always save after these

  // Anti-spazzing: Rate limiting and duplicate prevention
  private actionHistory: Array<{ action: string; timestamp: number }> = [];
  private recentActions: Map<string, number> = new Map();
  private readonly MIN_ACTION_INTERVAL = 300; // 300ms minimum between actions
  private readonly MAX_ACTIONS_PER_SECOND = 5;
  private readonly DEDUP_WINDOW = 2000; // 2 seconds for duplicate detection
  private lastActionTime: number = 0;

  // LLM service for AI script generation
  private llmService: LLMService | null = null;
  private scriptCache: Map<string, string> = new Map();

  private readonly storageStatePath: string;
  private readonly stateDir: string;
  private readonly headless: boolean;
  private readonly timeouts: Required<TimeoutConfig>;
  private readonly userDataDir: string | undefined;
  private readonly extensionPaths: string[] | undefined;

  constructor(config: {
    agentId: string;
    stateDir?: string;
    headless?: boolean;
    timeouts?: TimeoutConfig;
    userDataDir?: string; // Persistent user data directory for extensions
    extensionPaths?: string[]; // Paths to extension directories (e.g., 1Password)
  }) {
    this.stateDir = config.stateDir || path.join(process.cwd(), '.mcp-browser-state');
    this.storageStatePath = path.join(this.stateDir, `${config.agentId}-state.json`);
    this.headless = config.headless ?? true;
    this.userDataDir = config.userDataDir;
    this.extensionPaths = config.extensionPaths;

    // Configurable timeouts with defaults
    this.timeouts = {
      navigation: config.timeouts?.navigation || 30000,
      action: config.timeouts?.action || 5000,
      element: config.timeouts?.element || 10000,
      visibility: config.timeouts?.visibility || 10000,
    };
  }

  /**
   * Initialize LLM service for AI script generation
   */
  initializeLLM(config: LLMConfig): void {
    try {
      this.llmService = new LLMService(config);
      if (this.llmService.isEnabled()) {
        console.error(`✅ LLM Service initialized: ${config.type}`);
      }
    } catch (error) {
      console.error(`⚠️  LLM Service initialization failed: ${error}`);
      this.llmService = null;
    }
  }

  /**
   * Check if LLM service is available
   */
  isLLMEnabled(): boolean {
    return this.llmService !== null && this.llmService.isEnabled();
  }

  /**
   * Generate and execute script from natural language
   */
  async executeTaskWithAIScript(description: string): Promise<any> {
    if (!this.isLLMEnabled()) {
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

      const generated = await this.llmService!.generateScript(description, context);
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

      const healedScript = await this.llmService!.selfHeal(
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
   * Get available elements on page (for context)
   */
  private async getAvailableElements(page: Page): Promise<any[]> {
    try {
      return await page.evaluate(() => {
        // @ts-expect-error - This code runs in browser context
        const elements = Array.from(document.querySelectorAll('button, a, input, select, textarea'));
        return elements.slice(0, 20).map((el: any) => ({
          tag: el.tagName,
          id: el.id,
          className: el.className,
          textContent: el.textContent?.trim().substring(0, 50),
          type: el.getAttribute('type'),
          role: el.getAttribute('role')
        }));
      });
    } catch {
      return [];
    }
  }

  /**
   * Hash task description for caching
   */
  private hashTask(description: string): string {
    return createHash('sha256').update(description).digest('hex');
  }

  /**
   * Execute generated Playwright script
   * Simplified parser - converts common patterns to actions
   */
  private async executeGeneratedScript(script: string): Promise<any> {
    const page = await this.getPage();
    const actions: BrowserAction[] = [];

    // Extract navigate
    const navMatch = script.match(/goto\(['"]([^'"]+)['"]\)/);
    if (navMatch) {
      actions.push({ type: 'navigate', url: navMatch[1] });
    }

    // Extract clicks (simplified - in production, use proper parser)
    const clickMatches = script.matchAll(/getBy(?:Role|Text|Label)\([^)]+\)\.click\(\)/g);
    for (const match of clickMatches) {
      // Extract text/role from match
      const textMatch = match[0].match(/['"]([^'"]+)['"]/);
      if (textMatch) {
        actions.push({ 
          type: 'click', 
          locatorText: textMatch[1],
          locatorType: match[0].includes('getByRole') ? 'role' : 
                      match[0].includes('getByLabel') ? 'label' : 'text'
        });
      }
    }

    // Extract fills
    const fillMatches = script.matchAll(/fill\(['"]([^'"]+)['"]\)/g);
    for (const match of fillMatches) {
      const prevLine = script.substring(0, script.indexOf(match[0]));
      const labelMatch = prevLine.match(/getBy(?:Label|Placeholder)\(['"]([^'"]+)['"]\)/);
      if (labelMatch) {
        actions.push({ 
          type: 'fill', 
          locatorText: labelMatch[1],
          value: match[1]
        });
      }
    }

    // Execute actions
    for (const action of actions) {
      await this.executeAction(action);
    }

    return { success: true, actionsExecuted: actions.length };
  }

  /**
   * Initialize browser with persistent state
   */
  async initialize(): Promise<void> {
    // Check if browser is still connected
    if (this.browser && !this.browser.isConnected()) {
      console.error('⚠️  Browser disconnected, cleaning up...');
      this.browser = null;
      this.context = null;
      this.page = null;
      this.currentUrl = null;
    }

    // Check if context is still valid
    if (this.context) {
      try {
        await this.context.pages(); // Throws if context closed
      } catch {
        console.error('⚠️  Context closed, resetting...');
        this.context = null;
        this.page = null;
        this.currentUrl = null;
      }
    }

    // Check if page is still valid
    if (this.page) {
      if (this.page.isClosed()) {
        console.error('⚠️  Page closed, resetting...');
        this.page = null;
        this.currentUrl = null;
      } else {
        try {
          // Quick liveness check with timeout
          await Promise.race([
            this.page.evaluate(() => true),
            new Promise((_, reject) =>
              setTimeout(() => reject(new Error('Timeout')), 2000)
            )
          ]);
        } catch {
          console.error('⚠️  Page unresponsive, resetting...');
          this.page = null;
          this.currentUrl = null;
        }
      }
    }

    // Use launchPersistentContext if userDataDir is provided (for extensions)
    // Otherwise use regular launch + newContext
    if (this.userDataDir) {
      // Ensure userDataDir exists
      await fs.mkdir(this.userDataDir, { recursive: true });

      if (!this.context) {
        let storageState = undefined;
        
        // Try to load existing storage state
        try {
          await fs.access(this.storageStatePath);
          const stats = await fs.stat(this.storageStatePath);
          if (stats.size > 0) {
            const stateContent = await fs.readFile(this.storageStatePath, 'utf-8');
            const state = JSON.parse(stateContent);
            if (state.cookies || state.origins) {
              storageState = state;
              this.lastStateHash = this.hashState(state);
              console.error('✅ Loaded persistent browser state');
            }
          }
        } catch (error) {
          console.error('ℹ️  No existing state found, starting fresh');
        }

        // Get system timezone for better realism
        const systemTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        // Build args - remove extension-disabling flags when extensions are enabled
        const args = [
          '--disable-blink-features=AutomationControlled',
          '--disable-dev-shm-usage',
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-web-security',
          '--disable-features=IsolateOrigins,site-per-process',
          '--disable-site-isolation-trials',
          '--disable-infobars',
          '--disable-notifications',
          '--disable-popup-blocking',
          '--disable-translate',
          '--disable-background-timer-throttling',
          '--disable-backgrounding-occluded-windows',
          '--disable-renderer-backgrounding',
          '--disable-features=TranslateUI',
          '--disable-ipc-flooding-protection',
          '--enable-features=NetworkService,NetworkServiceInProcess',
          '--force-color-profile=srgb',
          '--metrics-recording-only',
          '--use-mock-keychain'
        ];

        // Add extension paths if provided
        if (this.extensionPaths && this.extensionPaths.length > 0) {
          for (const extPath of this.extensionPaths) {
            args.push(`--load-extension=${extPath}`);
          }
          console.error(`✅ Loading ${this.extensionPaths.length} extension(s)`);
        }

        this.context = await chromium.launchPersistentContext(this.userDataDir, {
          headless: this.headless,
          timeout: 0,
          args,
          viewport: { width: 1920, height: 1080 },
          userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
          locale: 'en-US',
          timezoneId: systemTimezone || 'America/Los_Angeles',
          permissions: [],
          extraHTTPHeaders: {
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
          },
          ignoreHTTPSErrors: false,
          javaScriptEnabled: true
        });

        // Load storage state if available (cookies, localStorage, etc.)
        if (storageState) {
          await this.context.addCookies(storageState.cookies || []);
          // Note: localStorage and sessionStorage need to be set per page
        }

        // Inject stealth script
        await this.injectStealthScript(this.context);
        
        this.page = this.context.pages()[0] || await this.context.newPage();
        console.error('🌐 Browser launched with persistent context (extensions enabled)');
      }
    } else {
      // Original launch + newContext approach (no extensions)
      if (!this.browser) {
        this.browser = await chromium.launch({
          headless: this.headless,
          timeout: 0,
          args: [
            // Core stealth - disable automation indicators
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            
            // Site isolation and security (helps with stealth)
            '--disable-features=IsolateOrigins,site-per-process,AutomationControlled',
            '--disable-site-isolation-trials',
            
            // UI elements that indicate automation
            '--disable-infobars',
            '--disable-notifications',
            '--disable-popup-blocking',
            '--disable-translate',
            
            // Background throttling (makes browser look more legitimate)
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            
            // Additional features
            '--disable-features=TranslateUI,BlinkGenPropertyTrees',
            '--disable-ipc-flooding-protection',
            '--enable-features=NetworkService,NetworkServiceInProcess',
            '--force-color-profile=srgb',
            '--metrics-recording-only',
            '--use-mock-keychain',
            '--disable-component-extensions-with-background-pages',
            
            // Additional stealth flags
            '--disable-sync',
            '--disable-component-update',
            '--no-default-browser-check',
            '--no-first-run',
            '--password-store=basic',
            '--disable-default-apps',
            '--disable-extensions-file-access-check',
            '--disable-extensions-http-throttling',
            
            // WebRTC (can be used for fingerprinting)
            '--disable-webrtc',
            '--disable-webrtc-hw-encoding',
            '--disable-webrtc-hw-decoding'
          ]
        });

        console.error('🌐 Browser launched');
      }

      // Create or reuse context with loaded state
      if (!this.context) {
        let storageState = undefined;

      try {
        await fs.access(this.storageStatePath);

        // Check file is not empty
        const stats = await fs.stat(this.storageStatePath);
        if (stats.size === 0) {
          console.error('⚠️  State file is empty, starting fresh');
          // Optionally backup empty file
          try {
            await fs.rename(this.storageStatePath, this.storageStatePath + '.empty.backup');
          } catch {}
        } else {
          // Read and validate JSON structure
          const stateContent = await fs.readFile(this.storageStatePath, 'utf-8');
          const state = JSON.parse(stateContent);

          // Validate state structure
          if (!state.cookies && !state.origins) {
            throw new Error('Invalid state file structure');
          }

          storageState = state;
          // Initialize hash from loaded state
          this.lastStateHash = this.hashState(state);
          console.error('✅ Loaded persistent browser state');
        }
      } catch (error) {
        if (error instanceof SyntaxError) {
          console.error('⚠️  State file contains invalid JSON, starting fresh');
          // Backup corrupted file
          try {
            await fs.rename(this.storageStatePath, this.storageStatePath + '.corrupted.backup');
          } catch {}
        } else if (error instanceof Error && error.message.includes('Invalid state')) {
          console.error('⚠️  Invalid state file structure, starting fresh');
          // Backup invalid file
          try {
            await fs.rename(this.storageStatePath, this.storageStatePath + '.invalid.backup');
          } catch {}
        } else {
          console.error('ℹ️  No existing state found, starting fresh');
        }
      }

      // Get system timezone for better realism
      const systemTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      
      this.context = await this.browser.newContext({
        viewport: { width: 1920, height: 1080 },
        storageState,
        // Updated to Chrome 131 (more recent, less suspicious)
        userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        locale: 'en-US',
        timezoneId: systemTimezone || 'America/Los_Angeles',
        permissions: [],
        extraHTTPHeaders: {
          'Accept-Language': 'en-US,en;q=0.9',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
          'Accept-Encoding': 'gzip, deflate, br, zstd',
          'Sec-Fetch-Dest': 'document',
          'Sec-Fetch-Mode': 'navigate',
          'Sec-Fetch-Site': 'none',
          'Sec-Fetch-User': '?1',
          'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
          'Sec-Ch-Ua-Mobile': '?0',
          'Sec-Ch-Ua-Platform': '"macOS"',
          'Upgrade-Insecure-Requests': '1',
          'Cache-Control': 'max-age=0'
        },
        // Add stealth script at context level so it applies to all pages
        ignoreHTTPSErrors: false,
        javaScriptEnabled: true
      });

        // Inject comprehensive stealth script at context level
        await this.injectStealthScript(this.context);
      }

      // Create page if needed
      if (!this.page) {
        this.page = await this.context.newPage();
      }
    }
  }

  /**
   * Inject stealth script to bypass bot detection
   * Enhanced with additional techniques from GitHub best practices
   */
  private async injectStealthScript(context: BrowserContext): Promise<void> {
    await context.addInitScript(`
        // ===== CORE STEALTH: Hide webdriver =====
        Object.defineProperty(navigator, 'webdriver', {
          get: () => false,
        });

        // ===== HIDE AUTOMATION IN DOCUMENT =====
        // Hide common automation detection properties
        Object.defineProperty(document, '$cdc_asdjflasutopfhvcZLmcfl_', {
          get: () => undefined,
          configurable: true
        });
        Object.defineProperty(document, '$chrome_asyncScriptInfo', {
          get: () => undefined,
          configurable: true
        });
        Object.defineProperty(document, '__$webdriverAsyncExecutor', {
          get: () => undefined,
          configurable: true
        });
        Object.defineProperty(document, '__driver_evaluate', {
          get: () => undefined,
          configurable: true
        });
        Object.defineProperty(document, '__webdriver_evaluate', {
          get: () => undefined,
          configurable: true
        });
        Object.defineProperty(document, '__selenium_evaluate', {
          get: () => undefined,
          configurable: true
        });
        Object.defineProperty(document, '__fxdriver_evaluate', {
          get: () => undefined,
          configurable: true
        });
        Object.defineProperty(document, '__driver_unwrapped', {
          get: () => undefined,
          configurable: true
        });
        Object.defineProperty(document, '__webdriver_unwrapped', {
          get: () => undefined,
          configurable: true
        });
        Object.defineProperty(document, '__selenium_unwrapped', {
          get: () => undefined,
          configurable: true
        });
        Object.defineProperty(document, '__fxdriver_unwrapped', {
          get: () => undefined,
          configurable: true
        });

        // ===== OVERRIDE FUNCTION.TOSTRING =====
        // Prevent detection via function.toString() calls
        const originalToString = Function.prototype.toString;
        Function.prototype.toString = function() {
          if (this === navigator.webdriver || 
              (typeof this === 'function' && this.toString === originalToString)) {
            return 'function webdriver() { [native code] }';
          }
          if (this === navigator.permissions.query) {
            return 'function query() { [native code] }';
          }
          return originalToString.call(this);
        };

        // ===== CHROME OBJECT: Make it look like real Chrome =====
        window.chrome = {
          runtime: {},
          loadTimes: function() {},
          csi: function() {},
          app: {}
        };

        // ===== PERMISSIONS API: Realistic behavior =====
        const originalQuery = navigator.permissions.query;
        navigator.permissions.query = (parameters) =>
          parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters);

        // ===== NOTIFICATION.PERMISSION =====
        Object.defineProperty(Notification, 'permission', {
          get: () => 'default',
          configurable: true
        });

        // ===== PLUGINS: Realistic plugin array =====
        Object.defineProperty(navigator, 'plugins', {
          get: () => {
            const plugins = [];
            // Chrome PDF Plugin
            plugins.push({
              0: { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
              description: 'Portable Document Format',
              filename: 'internal-pdf-viewer',
              length: 1,
              name: 'Chrome PDF Plugin'
            });
            // Chrome PDF Viewer
            plugins.push({
              0: { type: 'application/pdf', suffixes: 'pdf', description: '' },
              description: '',
              filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
              length: 1,
              name: 'Chrome PDF Viewer'
            });
            // Native Client
            plugins.push({
              0: { type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable' },
              1: { type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable' },
              description: '',
              filename: 'internal-nacl-plugin',
              length: 2,
              name: 'Native Client'
            });
            return plugins;
          },
        });

        // ===== LANGUAGES: Realistic language array =====
        Object.defineProperty(navigator, 'languages', {
          get: () => ['en-US', 'en'],
        });

        // ===== HARDWARE CONCURRENCY: Realistic CPU cores =====
        Object.defineProperty(navigator, 'hardwareConcurrency', {
          get: () => 8, // Common modern CPU core count
        });

        // ===== DEVICE MEMORY: Realistic RAM =====
        Object.defineProperty(navigator, 'deviceMemory', {
          get: () => 8, // 8GB RAM
        });

        // ===== PLATFORM: Ensure consistent platform =====
        Object.defineProperty(navigator, 'platform', {
          get: () => 'MacIntel',
        });

        // ===== CANVAS FINGERPRINTING PROTECTION =====
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
          if (type === 'image/png' || type === 'image/jpeg') {
            const context = this.getContext('2d');
            if (context) {
              const imageData = context.getImageData(0, 0, this.width, this.height);
              // Add tiny random noise to prevent fingerprinting
              for (let i = 0; i < imageData.data.length; i += 4) {
                if (Math.random() < 0.01) { // 1% of pixels
                  imageData.data[i] += Math.random() < 0.5 ? 1 : -1;
                }
              }
              context.putImageData(imageData, 0, 0);
            }
          }
          return originalToDataURL.apply(this, arguments);
        };

        // ===== WEBGL FINGERPRINTING PROTECTION =====
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
          if (parameter === 37445) { // UNMASKED_VENDOR_WEBGL
            return 'Intel Inc.';
          }
          if (parameter === 37446) { // UNMASKED_RENDERER_WEBGL
            return 'Intel Iris OpenGL Engine';
          }
          return getParameter.apply(this, arguments);
        };

        // ===== AUDIO CONTEXT FINGERPRINTING PROTECTION =====
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (AudioContext) {
          const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
          AudioContext.prototype.createAnalyser = function() {
            const analyser = originalCreateAnalyser.apply(this, arguments);
            const originalGetFloatFrequencyData = analyser.getFloatFrequencyData;
            analyser.getFloatFrequencyData = function(array) {
              originalGetFloatFrequencyData.apply(this, arguments);
              // Add tiny random noise
              for (let i = 0; i < array.length; i++) {
                array[i] += (Math.random() - 0.5) * 0.0001;
              }
            };
            return analyser;
          };
        }

        // ===== PROPERTY DESCRIPTORS: Prevent detection =====
        Object.defineProperty(navigator, 'maxTouchPoints', {
          get: () => 0,
        });

        // ===== CONNECTION: Realistic connection info =====
        if (navigator.connection) {
          Object.defineProperty(navigator.connection, 'rtt', {
            get: () => 50 + Math.random() * 50, // 50-100ms
          });
          Object.defineProperty(navigator.connection, 'downlink', {
            get: () => 10 + Math.random() * 5, // 10-15 Mbps
          });
          Object.defineProperty(navigator.connection, 'effectiveType', {
            get: () => '4g',
          });
        }

        // ===== BATTERY API: Realistic battery info =====
        if (navigator.getBattery) {
          const originalGetBattery = navigator.getBattery;
          navigator.getBattery = function() {
            return originalGetBattery.call(this).then(battery => {
              // Add slight randomization to battery level
              Object.defineProperty(battery, 'level', {
                get: () => Math.min(1, Math.max(0, 0.7 + Math.random() * 0.3)),
                configurable: true
              });
              return battery;
            });
          };
        }

        // ===== MEDIA DEVICES: Randomize device IDs =====
        if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
          const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
          navigator.mediaDevices.enumerateDevices = function() {
            return originalEnumerateDevices.call(this).then(devices => {
              // Add slight randomization to device IDs to prevent fingerprinting
              return devices.map(device => ({
                ...device,
                deviceId: device.deviceId ? device.deviceId + Math.random().toString(36).substring(2, 7) : device.deviceId
              }));
            });
          };
        }

        // ===== HIDE AUTOMATION IN WINDOW =====
        // Remove automation-related properties from window
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

        // ===== CONSOLE DEBUG: Remove automation traces =====
        const originalLog = console.log;
        const originalWarn = console.warn;
        const originalError = console.error;
        
        console.log = function(...args) {
          const str = args.join(' ');
          if (str.includes('webdriver') || str.includes('automation') || 
              str.includes('ChromeDriver') || str.includes('Selenium')) {
            return;
          }
          return originalLog.apply(console, arguments);
        };
        
        console.warn = function(...args) {
          const str = args.join(' ');
          if (str.includes('webdriver') || str.includes('automation') || 
              str.includes('ChromeDriver') || str.includes('Selenium')) {
            return;
          }
          return originalWarn.apply(console, arguments);
        };
        
        console.error = function(...args) {
          const str = args.join(' ');
          if (str.includes('webdriver') || str.includes('automation') || 
              str.includes('ChromeDriver') || str.includes('Selenium')) {
            return;
          }
          return originalError.apply(console, arguments);
        };
      `);
  }

  /**
   * Setup popup/new window handling
   */
  private setupPopupHandling(): void {
    if (!this.page) return;

    this.page.on('popup', async (popup) => {
      console.error('🪟 Popup detected, handling...');
      try {
        // Wait for popup to load
        await popup.waitForLoadState('domcontentloaded');
        // For now, auto-close popups (could be configurable)
        await popup.close();
        console.error('✅ Popup closed');
      } catch (error) {
        console.error('⚠️  Error handling popup:', error instanceof Error ? error.message : String(error));
        // Try to close anyway
        try {
          await popup.close();
        } catch {}
      }
    });
  }

  /**
   * Get current page (ensure initialized) - FIXED to prevent multiple tabs
   */
  async getPage(): Promise<Page> {
    try {
      await this.initialize();

      // Validate page is responsive
      if (this.page) {
        try {
          await this.page.evaluate(() => true); // Quick liveness check
          return this.page;
        } catch {
          // Page is dead, reset it
          this.page = null;
          this.currentUrl = null;
        }
      }

      // Re-initialize if page is missing
      await this.initialize();
      return this.page!;
    } catch (error) {
      // Reset and retry once
      console.error('🔄 Browser recovery attempt...');
      this.browser = null;
      this.context = null;
      this.page = null;
      this.currentUrl = null;
      await this.initialize();
      return this.page!;
    }
  }

  /**
   * Intelligent element finder using Playwright's Locator API
   * FIXED: Multi-strategy fallback chain for better reliability
   */
  private async findElement(
    page: Page,
    action: BrowserAction
  ): Promise<Locator | null> {
    const text = action.locatorText || action.selector || '';
    const locatorType = action.locatorType || 'text';

    // If specific type requested, try that first, then fallback
    if (locatorType !== 'css') {
      const primaryLocator = await this.tryFindByType(page, action, locatorType);
      if (primaryLocator) {
        const count = await primaryLocator.count();
        if (count > 0) {
          if (count > 1) {
            console.error(`⚠️  Found ${count} matching elements, using first`);
          }
          return primaryLocator;
        }
      }
    }

    // Fallback chain: try multiple strategies
    const strategies: Array<'role' | 'text' | 'label' | 'placeholder' | 'testid' | 'css'> =
      locatorType === 'role' ? ['role', 'text', 'css'] :
      locatorType === 'label' ? ['label', 'placeholder', 'text', 'css'] :
      locatorType === 'text' ? ['text', 'role', 'css'] :
      ['text', 'role', 'label', 'placeholder', 'css'];

    for (const strategy of strategies) {
      if (strategy === locatorType) continue; // Already tried

      const locator = await this.tryFindByType(page, action, strategy);
      if (locator) {
        const count = await locator.count();
        if (count > 0) {
          console.error(`✅ Found element using ${strategy} strategy`);
          return locator;
        }
      }
    }

    return null;
  }

  /**
   * Try finding element by specific locator type
   */
  private async tryFindByType(
    page: Page,
    action: BrowserAction,
    locatorType: 'role' | 'text' | 'label' | 'placeholder' | 'testid' | 'css'
  ): Promise<Locator | null> {
    const text = action.locatorText || action.selector || '';

    try {
      switch (locatorType) {
        case 'role':
          return page.getByRole('button', { name: text, exact: false })
            .or(page.getByRole('link', { name: text, exact: false }))
            .or(page.getByRole('menuitem', { name: text, exact: false }))
            .first();

        case 'text':
          return page.getByText(text, { exact: false }).first();

        case 'label':
          return page.getByLabel(text, { exact: false }).first();

        case 'placeholder':
          return page.getByPlaceholder(text, { exact: false }).first();

        case 'testid':
          return page.getByTestId(text).first();

        case 'css':
        default:
          if (action.selector) {
            return page.locator(action.selector).first();
          }
          return null;
      }
    } catch {
      return null;
    }
  }

  /**
   * Execute action with intelligent retry and smart refresh
   */
  private async executeWithRetry<T>(
    fn: () => Promise<T>,
    maxRetries: number = 3,
    delay: number = 1000
  ): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        if (attempt < maxRetries) {
          // Check if should refresh instead of just retrying
          if (await this.shouldRefresh(lastError, attempt)) {
            console.error(`🔄 Refreshing page before retry ${attempt}/${maxRetries}...`);
            await this.smartRefresh();
            // Continue to retry after refresh
          } else {
            // Standard exponential backoff with jitter
            const waitTime = delay * Math.pow(2, attempt - 1) + Math.random() * 500;
            console.error(`⚠️  Attempt ${attempt} failed, retrying in ${Math.round(waitTime)}ms...`);
            await new Promise(resolve => setTimeout(resolve, waitTime));
          }
        }
      }
    }

    throw lastError || new Error('Action failed after retries');
  }

  /**
   * Hash state for change detection
   */
  private hashState(state: any): string {
    const stateString = JSON.stringify(state);
    return createHash('sha256').update(stateString).digest('hex');
  }

  /**
   * Save browser state - OPTIMIZED: Debounced, change detection, async
   */
  async saveState(force: boolean = false): Promise<void> {
    if (!this.context) return;

    // Check context is still valid before saving
    try {
      await this.context.pages();
    } catch {
      console.error('⚠️  Context closed, cannot save state');
      return;
    }

    try {
      const state = await this.context.storageState();
      const stateHash = this.hashState(state);

      // Skip save if state hasn't changed (unless forced)
      if (!force && stateHash === this.lastStateHash) {
        return; // No changes, skip save
      }

      this.lastStateHash = stateHash;
      await fs.mkdir(this.stateDir, { recursive: true });

      // Atomic write: write to temp file first
      const tempPath = this.storageStatePath + '.tmp';
      // Use compact JSON (no pretty printing) for smaller files
      await fs.writeFile(tempPath, JSON.stringify(state));

      // Then rename atomically (prevents corruption if process crashes mid-write)
      await fs.rename(tempPath, this.storageStatePath);

      console.error('💾 Browser state saved');
    } catch (error) {
      console.error('❌ Failed to save state:', error);

      // Clean up temp file if exists
      try {
        await fs.unlink(this.storageStatePath + '.tmp');
      } catch {}

      // Handle permission errors specifically
      if (error instanceof Error && (error as any).code === 'EACCES') {
        console.error(`❌ Permission denied: Cannot write to ${this.stateDir}`);
      }
    }
  }

  /**
   * Schedule state save with debouncing (optimized)
   */
  private scheduleStateSave(actionType: string, force: boolean = false): void {
    // Clear existing timer
    if (this.stateSaveTimer) {
      clearTimeout(this.stateSaveTimer);
      this.stateSaveTimer = null;
    }

    // Force save for important actions (navigation, login, etc.)
    const shouldForceSave = force || this.FORCE_SAVE_ACTIONS.includes(actionType);

    if (shouldForceSave) {
      // Save immediately for important actions
      this.pendingStateSave = this.saveState(true).catch(err => {
        console.error('⚠️  Background state save failed:', err);
      });
    } else {
      // Debounce for other actions (clicks, waits, etc.)
      this.stateSaveTimer = setTimeout(() => {
        this.pendingStateSave = this.saveState(false).catch(err => {
          console.error('⚠️  Background state save failed:', err);
        });
        this.stateSaveTimer = null;
      }, this.STATE_SAVE_DEBOUNCE_MS);
    }
  }

  /**
   * Wait for any pending state saves to complete
   */
  async flushStateSave(): Promise<void> {
    // Clear debounce timer and save immediately
    if (this.stateSaveTimer) {
      clearTimeout(this.stateSaveTimer);
      this.stateSaveTimer = null;
    }

    // Wait for any pending save
    if (this.pendingStateSave) {
      await this.pendingStateSave;
      this.pendingStateSave = null;
    }

    // Force a final save
    await this.saveState(true);
  }

  /**
   * Clear saved state
   */
  async clearState(): Promise<void> {
    try {
      await fs.unlink(this.storageStatePath);
      console.error('🗑️  Browser state cleared');
    } catch {
      // File might not exist
    }
  }

  /**
   * Check if state exists
   */
  async hasState(): Promise<boolean> {
    try {
      await fs.access(this.storageStatePath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Check if page is currently loading
   */
  private async isPageLoading(page: Page): Promise<boolean> {
    try {
      const loadingState = await page.evaluate(() => {
        // @ts-expect-error - This code runs in browser context, DOM types are available
        if (document.readyState !== 'complete') {
          return true;
        }
        
        // Check for loading indicators
        const loadingSelectors = [
          '.loading', '.spinner', '[data-loading="true"]',
          '.skeleton', '.shimmer', '[aria-busy="true"]',
          '.loader', '[class*="loading"]'
        ];
        
        for (const selector of loadingSelectors) {
          try {
            // @ts-expect-error - This code runs in browser context
            if (document.querySelector(selector)) {
              return true;
            }
          } catch {
            // Invalid selector, continue
          }
        }
        
        return false;
      });
      
      return loadingState;
    } catch {
      return false; // Assume not loading if check fails
    }
  }

  /**
   * Wait for page to finish loading intelligently
   */
  private async waitForPageReady(page: Page, timeout: number = 10000): Promise<void> {
    const startTime = Date.now();
    const checkInterval = 500;

    // Wait for DOM to be ready first
    try {
      await page.waitForLoadState('domcontentloaded', { timeout: 5000 });
    } catch {
      // Continue even if DOM not ready
    }

    // Poll for loading indicators to disappear
    while (Date.now() - startTime < timeout) {
      const isLoading = await this.isPageLoading(page);
      if (!isLoading) {
        return;
      }
      await page.waitForTimeout(checkInterval);
    }
  }

  /**
   * Check if action is duplicate (anti-spazzing)
   */
  private isDuplicateAction(action: BrowserAction): boolean {
    const actionKey = `${action.type}:${action.selector || action.url || action.locatorText}`;
    const lastExecution = this.recentActions.get(actionKey);
    
    if (lastExecution) {
      const timeSinceLastExecution = Date.now() - lastExecution;
      if (timeSinceLastExecution < this.DEDUP_WINDOW) {
        return true; // Duplicate within window
      }
    }
    
    return false;
  }

  /**
   * Record action execution (anti-spazzing)
   */
  private recordAction(action: BrowserAction): void {
    const actionKey = `${action.type}:${action.selector || action.url || action.locatorText}`;
    this.recentActions.set(actionKey, Date.now());
    this.lastActionTime = Date.now();
    
    // Clean up old entries
    const now = Date.now();
    for (const [key, timestamp] of this.recentActions.entries()) {
      if (now - timestamp > this.DEDUP_WINDOW) {
        this.recentActions.delete(key);
      }
    }
    
    // Track action history for rate limiting
    this.actionHistory.push({
      action: action.type,
      timestamp: Date.now()
    });
    
    // Keep only last second of history
    this.actionHistory = this.actionHistory.filter(
      entry => Date.now() - entry.timestamp < 1000
    );
  }

  /**
   * Wait if rate limited (anti-spazzing)
   */
  private async waitIfRateLimited(): Promise<void> {
    const now = Date.now();
    
    // Check minimum interval since last action
    if (this.lastActionTime > 0) {
      const timeSinceLastAction = now - this.lastActionTime;
      if (timeSinceLastAction < this.MIN_ACTION_INTERVAL) {
        const waitTime = this.MIN_ACTION_INTERVAL - timeSinceLastAction;
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    }
    
    // Check actions per second limit
    const recentActions = this.actionHistory.filter(
      entry => now - entry.timestamp < 1000
    );
    
    if (recentActions.length >= this.MAX_ACTIONS_PER_SECOND) {
      const oldestAction = recentActions[0];
      const waitTime = 1000 - (now - oldestAction.timestamp);
      if (waitTime > 0) {
        await new Promise(resolve => setTimeout(resolve, waitTime));
      }
    }
  }

  /**
   * Navigate to URL - INTELLIGENT: Loading detection, no duplicates
   */
  async navigate(url: string): Promise<void> {
    const page = await this.getPage();

    // Don't navigate if already on the same URL
    if (this.currentUrl === url) {
      console.error(`ℹ️  Already on ${url}`);
      return;
    }

    // Check for duplicate navigation
    const navAction: BrowserAction = { type: 'navigate', url };
    if (this.isDuplicateAction(navAction)) {
      console.error(`⏭️  Skipping duplicate navigation to ${url}`);
      return;
    }

    // Wait if rate limited
    await this.waitIfRateLimited();

    await this.executeWithRetry(async () => {
      try {
        // Check if page is currently loading
        if (await this.isPageLoading(page)) {
          console.error('⏳ Page is loading, waiting...');
          await this.waitForPageReady(page, 5000);
        }

        // Use domcontentloaded instead of networkidle (faster, more reliable)
        await page.goto(url, {
          waitUntil: 'domcontentloaded',
          timeout: this.timeouts.navigation
        });
        
        // Wait for page to be ready (but not networkidle - too slow)
        await this.waitForPageReady(page, 5000);
        
        this.currentUrl = page.url();
        this.recordAction(navAction);
        console.error(`🌐 Navigated to ${url}`);
      } catch (error) {
        // Distinguish network errors
        const errorMsg = error instanceof Error ? error.message : String(error);
        if (errorMsg.includes('net::') || errorMsg.includes('Navigation')) {
          throw new Error(`Network error navigating to ${url}: ${errorMsg}`);
        }
        throw error;
      }
    });
  }

  /**
   * Execute a single action - FIXED: Uses Locator API, retry logic, and action locking
   */
  async executeAction(action: BrowserAction): Promise<void> {
    // Queue actions to prevent concurrent execution
    this.actionQueue = this.actionQueue.then(async () => {
      if (this.isExecuting) {
        throw new Error('Action already executing');
      }
      this.isExecuting = true;
      try {
        await this.executeActionInternal(action);
      } finally {
        this.isExecuting = false;
      }
    });

    return this.actionQueue;
  }

  /**
   * Internal action execution (called from queue)
   */
  private async executeActionInternal(action: BrowserAction): Promise<void> {
    // Check for duplicate action (anti-spazzing)
    if (this.isDuplicateAction(action)) {
      console.error(`⏭️  Skipping duplicate action: ${action.type}`);
      return;
    }

    // Wait if rate limited (anti-spazzing)
    await this.waitIfRateLimited();

    const page = await this.getPage();

    // Check if page is loading before action
    if (await this.isPageLoading(page)) {
      console.error('⏳ Page is loading, waiting before action...');
      await this.waitForPageReady(page, 3000);
    }

    switch (action.type) {
      case 'navigate':
        if (action.url) {
          await this.navigate(action.url);
          // Schedule state save (navigation is important, save immediately)
          this.scheduleStateSave('navigate', true);
        }
        break;

      case 'click':
        await this.executeWithRetry(async () => {
          const locator = await this.findElement(page, action);
          if (!locator) {
            // Better error message with context
            const text = action.locatorText || action.selector || 'unknown';
            const currentUrl = page.url();
            let pageTitle = 'unknown';
            try {
              pageTitle = await page.title();
            } catch {}
            throw new Error(
              `Element not found: "${text}". ` +
              `Tried: ${action.locatorType || 'text'}. ` +
              `Current URL: ${currentUrl}. ` +
              `Page title: ${pageTitle}`
            );
          }

          // Wait for element to be visible with retry logic
          let visible = false;
          for (let attempt = 1; attempt <= 3; attempt++) {
            try {
              await locator.waitFor({
                state: 'visible',
                timeout: this.timeouts.visibility * attempt
              });
              visible = true;
              break;
            } catch {
              if (attempt === 3) throw new Error('Element never became visible');
            }
          }

          // Check if element is enabled
          const isEnabled = await locator.isEnabled().catch(() => false);
          if (!isEnabled) {
            throw new Error(`Element "${action.locatorText || action.selector}" is disabled`);
          }

          await locator.click({ timeout: this.timeouts.action, force: false });
          console.error(`✅ Clicked: ${action.locatorText || action.selector}`);
          
          // Record action (anti-spazzing)
          this.recordAction(action);
          
          // Brief wait after click for action to register
          await page.waitForTimeout(300);
          
          // Check if navigation happened (don't wait too long)
          try {
            await Promise.race([
              page.waitForNavigation({ timeout: 2000 }),
              page.waitForTimeout(1000)
            ]);
          } catch {
            // No navigation, that's fine
          }
          
          // Schedule debounced state save (clicks are less critical)
          this.scheduleStateSave('click', false);
        });
        break;

      case 'fill':
        await this.executeWithRetry(async () => {
          const locator = await this.findElement(page, action);
          if (!locator) {
            // Try direct input finding with better error context
            const text = action.locatorText || action.selector || '';
            const inputLocator = page.getByPlaceholder(text)
              .or(page.getByLabel(text))
              .first();

            const count = await inputLocator.count();
            if (count === 0) {
              const currentUrl = page.url();
              let pageTitle = 'unknown';
              try {
                pageTitle = await page.title();
              } catch {}
              throw new Error(
                `Input field not found: "${text}". ` +
                `Tried: placeholder, label. ` +
                `Current URL: ${currentUrl}. ` +
                `Page title: ${pageTitle}`
              );
            }

            await inputLocator.waitFor({ state: 'visible', timeout: this.timeouts.visibility });
            await inputLocator.fill(action.value || '', { timeout: this.timeouts.action });
          } else {
            await locator.waitFor({ state: 'visible', timeout: this.timeouts.visibility });
            await locator.fill(action.value || '', { timeout: this.timeouts.action });
          }
          console.error(`✅ Filled: ${action.locatorText || action.selector} with ${action.value}`);
          
          // Record action (anti-spazzing)
          this.recordAction(action);
          
          // Schedule state save (form fills are important, save immediately)
          this.scheduleStateSave('fill', true);
        });
        break;

      case 'select':
        await this.executeWithRetry(async () => {
          const locator = page.locator(action.selector || 'select').first();
          await locator.waitFor({ state: 'visible', timeout: this.timeouts.visibility });
          await locator.selectOption(action.value || '', { timeout: this.timeouts.action });
          console.error(`✅ Selected: ${action.value}`);
        });
        break;

      case 'wait':
        try {
          if (!page.isClosed()) {
            await page.waitForTimeout(action.duration || 1000);
          } else {
            console.error('⚠️  Page closed during wait, skipping');
          }
        } catch (error) {
          // Page closed during wait - log and continue
          console.error('⚠️  Page closed during wait:', error instanceof Error ? error.message : String(error));
        }
        break;

      case 'waitForSelector':
        if (action.selector) {
          await page.waitForSelector(action.selector, { timeout: this.timeouts.element, state: 'visible' });
        }
        break;

      case 'screenshot':
        if (action.path) {
          await page.screenshot({ path: action.path, fullPage: true });
        }
        break;

      case 'keyPress':
        if (action.key) {
          await page.keyboard.press(action.key);
          console.error(`✅ Pressed key: ${action.key}`);
        }
        break;

      case 'evaluate':
        if (action.code) {
          try {
            const result = await this.evaluateCode(page, action.code, action.args);
            console.error(`✅ Code executed successfully`);
            // Store result for potential retrieval
            (action as any).result = result;
          } catch (error) {
            throw new Error(`Code execution failed: ${error instanceof Error ? error.message : String(error)}`);
          }
        }
        break;

      case 'inspect':
        if (action.selector) {
          try {
            const elementInfo = await this.inspectElement(page, action.selector);
            console.error(`✅ Element inspected: ${action.selector}`);
            // Store result for potential retrieval
            (action as any).inspection = elementInfo;
          } catch (error) {
            throw new Error(`Element inspection failed: ${error instanceof Error ? error.message : String(error)}`);
          }
        }
        break;

      case 'injectScript':
        if (action.code) {
          try {
            await this.injectScript(page, action.code, action.runOnNewDocument || false);
            console.error(`✅ Script injected${action.runOnNewDocument ? ' (persistent)' : ''}`);
          } catch (error) {
            throw new Error(`Script injection failed: ${error instanceof Error ? error.message : String(error)}`);
          }
        }
        break;
    }
  }

  /**
   * Extract data from page
   */
  async extractData(selectors: string[]): Promise<ExtractedData> {
    const page = await this.getPage();
    const data: ExtractedData = {};

    for (const selector of selectors) {
      try {
        const locator = page.locator(selector);
        const count = await locator.count();
        const values: string[] = [];

        for (let i = 0; i < count; i++) {
          const text = await locator.nth(i).textContent();
          if (text) values.push(text.trim());
        }

        data[selector] = values.length > 0 ? values : null;
      } catch {
        data[selector] = null;
      }
    }

    return data;
  }

  /**
   * Take screenshot
   */
  async screenshot(): Promise<string> {
    const page = await this.getPage();
    const buffer = await page.screenshot({ type: 'png', fullPage: true });
    return buffer.toString('base64');
  }

  /**
   * Get current URL
   */
  async getCurrentUrl(): Promise<string> {
    const page = await this.getPage();
    this.currentUrl = page.url();
    return this.currentUrl;
  }

  /**
   * Get page title
   */
  async getPageTitle(): Promise<string> {
    const page = await this.getPage();
    return page.title();
  }

  /**
   * Inspect DOM element with full details
   */
  async inspectElement(page: Page, selector: string): Promise<any> {
    return await page.evaluate((sel) => {
      // @ts-expect-error - This code runs in browser context, DOM types are available
      const element = document.querySelector(sel);
      if (!element) return null;

      // Get XPath helper
      function getXPath(element: any): string {
        if (element.id) {
          return `//*[@id="${element.id}"]`;
        }
        // @ts-expect-error - This code runs in browser context
        if (element === document.body) {
          return '/html/body';
        }
        
        let ix = 0;
        const siblings = element.parentNode?.childNodes || [];
        for (let i = 0; i < siblings.length; i++) {
          const sibling = siblings[i];
          if (sibling === element) {
            const parent = element.parentNode;
            if (parent) {
              return `${getXPath(parent)}/${element.tagName.toLowerCase()}[${ix + 1}]`;
            }
          }
          if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
            ix++;
          }
        }
        return '';
      }

      // @ts-expect-error - This code runs in browser context
      const styles = window.getComputedStyle(element);
      
      return {
        element: {
          tagName: element.tagName,
          id: element.id,
          className: element.className,
          textContent: element.textContent?.trim().substring(0, 200),
        },
        attributes: Array.from(element.attributes).reduce((acc: any, attr: any) => {
          acc[attr.name] = attr.value;
          return acc;
        }, {} as Record<string, string>),
        computedStyles: {
          display: styles.display,
          visibility: styles.visibility,
          opacity: styles.opacity,
          position: styles.position,
          zIndex: styles.zIndex,
          width: styles.width,
          height: styles.height,
        },
        boundingBox: {
          x: element.getBoundingClientRect().x,
          y: element.getBoundingClientRect().y,
          width: element.getBoundingClientRect().width,
          height: element.getBoundingClientRect().height,
        },
        isVisible: element.offsetParent !== null,
        isEnabled: !(element as any).disabled,
        xpath: getXPath(element),
        possibleSelectors: {
          id: element.id ? `#${element.id}` : null,
          className: element.className ? `.${element.className.split(' ').filter(Boolean).join('.')}` : null,
          tagName: element.tagName.toLowerCase(),
          textContent: element.textContent?.trim().substring(0, 50),
          ariaLabel: element.getAttribute('aria-label') ? `[aria-label="${element.getAttribute('aria-label')}"]` : null,
          dataTestId: element.getAttribute('data-testid') ? `[data-testid="${element.getAttribute('data-testid')}"]` : null,
        },
        relationships: {
          parent: element.parentElement ? {
            tag: element.parentElement.tagName,
            id: element.parentElement.id,
            className: element.parentElement.className
          } : null,
          children: Array.from(element.children).map((c: any) => ({
            tag: c.tagName,
            id: c.id,
            className: c.className
          }))
        }
      };
    }, selector);
  }

  /**
   * Execute JavaScript code in browser context
   */
  async evaluateCode(page: Page, code: string, args?: any[]): Promise<any> {
    try {
      if (args && args.length > 0) {
        // Execute with arguments
        return await page.evaluate(
          ({ code, args }) => {
            try {
              // Create function from code string
              const func = new Function(...args.map((_, i) => `arg${i}`), `return (${code})`);
              return func(...args);
            } catch (error) {
              throw new Error(`Code execution error: ${error instanceof Error ? error.message : String(error)}`);
            }
          },
          { code, args }
        );
      } else {
        // Execute code directly
        return await page.evaluate(code);
      }
    } catch (error) {
      throw new Error(`Code execution failed: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Inject script into page (persistent or one-time)
   */
  async injectScript(page: Page, script: string, runOnNewDocument: boolean = false): Promise<void> {
    if (runOnNewDocument) {
      // Runs on every page load (persistent)
      await page.addInitScript(script);
    } else {
      // Runs once (current page)
      await page.evaluate(script);
    }
  }

  /**
   * Check if page should be refreshed (smart refresh logic)
   */
  async shouldRefresh(error: Error, attemptCount: number): Promise<boolean> {
    const errorMsg = error.message.toLowerCase();
    
    // Don't refresh for element not found (try alternatives first)
    if (errorMsg.includes('element not found') || errorMsg.includes('selector')) {
      return false;
    }
    
    // Don't refresh for auth errors (need login, not refresh)
    if (errorMsg.includes('unauthorized') || errorMsg.includes('authentication')) {
      return false;
    }
    
    // Refresh for stuck/loading errors
    if (errorMsg.includes('stuck') || errorMsg.includes('loading')) {
      return true;
    }
    
    // Refresh for blank/empty page
    if (errorMsg.includes('blank') || errorMsg.includes('empty')) {
      return true;
    }
    
    // Refresh for server errors (502/503/504)
    if (errorMsg.includes('502') || errorMsg.includes('503') || errorMsg.includes('504')) {
      return true;
    }
    
    // Refresh after multiple failed attempts
    if (attemptCount >= 3) {
      return true;
    }
    
    return false;
  }

  /**
   * Smart refresh with state preservation
   */
  async smartRefresh(): Promise<void> {
    if (!this.page) return;
    
    console.error('🔄 Refreshing page...');
    const currentUrl = this.page.url();
    
    try {
      await this.page.reload({ waitUntil: 'domcontentloaded' });
      await this.waitForPageReady(this.page, 5000);
      this.currentUrl = this.page.url();
      console.error('✅ Page refreshed successfully');
    } catch (error) {
      console.error('⚠️  Refresh failed, navigating to URL instead');
      // Fallback: navigate to current URL
      await this.navigate(currentUrl);
    }
  }

  /**
   * Install extension from Chrome Web Store
   * Automatically navigates to extensions page, enables developer mode, and installs the extension
   */
  async installExtensionFromWebStore(webStoreUrl: string): Promise<{ success: boolean; message: string }> {
    const page = await this.getPage();

    try {
      // Step 1: Navigate to chrome://extensions/ and enable Developer Mode
      console.error('📦 Setting up extension installation...');
      await this.navigate('chrome://extensions/');
      await page.waitForTimeout(1000); // Wait for page to load

      // Enable Developer Mode toggle
      const developerModeToggle = page.locator('#devMode').first();
      const isEnabled = await developerModeToggle.isChecked().catch(() => false);
      
      if (!isEnabled) {
        console.error('🔧 Enabling Developer Mode...');
        await developerModeToggle.click();
        await page.waitForTimeout(500);
      }

      // Step 2: Navigate to Chrome Web Store extension page
      console.error(`🌐 Navigating to Chrome Web Store: ${webStoreUrl}`);
      await this.navigate(webStoreUrl);
      await page.waitForTimeout(2000); // Wait for page to load

      // Step 3: Find and click "Add to Chrome" button
      // The button text can vary: "Add to Chrome", "Add to Chromium", etc.
      console.error('🔍 Looking for "Add to Chrome" button...');
      
      // Try multiple selectors for the Add to Chrome button
      const addButtonSelectors = [
        'button:has-text("Add to Chrome")',
        'button:has-text("Add to Chromium")',
        'button:has-text("Install")',
        '[aria-label*="Add to Chrome"]',
        '[aria-label*="Add to Chromium"]',
        'button.f-r',
        'button[data-test-id="install-button"]'
      ];

      let addButton = null;
      for (const selector of addButtonSelectors) {
        try {
          const button = page.locator(selector).first();
          if (await button.isVisible({ timeout: 2000 }).catch(() => false)) {
            addButton = button;
            console.error(`✅ Found button with selector: ${selector}`);
            break;
          }
        } catch (e) {
          // Try next selector
        }
      }

      if (!addButton) {
        // Fallback: try to find any button with "Add" in the text
        const allButtons = await page.locator('button').all();
        for (const button of allButtons) {
          const text = await button.textContent().catch(() => '');
          if (text && (text.includes('Add') || text.includes('Install'))) {
            addButton = button;
            console.error(`✅ Found button with text: ${text}`);
            break;
          }
        }
      }

      if (!addButton) {
        throw new Error('Could not find "Add to Chrome" button on the page');
      }

      // Step 4: Click the button
      console.error('🖱️  Clicking "Add to Chrome" button...');
      await addButton.click();
      await page.waitForTimeout(1000);

      // Step 5: Handle confirmation dialog
      // The dialog might appear in a new popup or as an overlay
      console.error('⏳ Waiting for installation confirmation...');
      
      // Wait for either:
      // 1. Dialog/popup with "Add extension" confirmation
      // 2. Success message
      // 3. Extension installed (check extensions page)
      
      // Try to find and click confirmation button
      const confirmSelectors = [
        'button:has-text("Add extension")',
        'button:has-text("Add")',
        'button:has-text("Confirm")',
        '[aria-label*="Add extension"]',
        'button#confirmButton',
        'button[data-test-id="confirm-button"]'
      ];

      let confirmed = false;
      for (const selector of confirmSelectors) {
        try {
          const confirmButton = page.locator(selector).first();
          if (await confirmButton.isVisible({ timeout: 3000 }).catch(() => false)) {
            await confirmButton.click();
            console.error('✅ Confirmed installation');
            confirmed = true;
            await page.waitForTimeout(1000);
            break;
          }
        } catch (e) {
          // Try next selector
        }
      }

      // Check if installation was successful by navigating back to extensions page
      await page.waitForTimeout(2000);
      await this.navigate('chrome://extensions/');
      await page.waitForTimeout(1000);

      // Look for the extension (it should be listed now)
      // We can't easily verify by name without knowing the extension ID,
      // but if we got here without errors, it likely worked
      
      console.error('✅ Extension installation process completed');
      return {
        success: true,
        message: 'Extension installation completed. Please verify on chrome://extensions/ page.'
      };

    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      console.error(`❌ Extension installation failed: ${errorMsg}`);
      return {
        success: false,
        message: `Extension installation failed: ${errorMsg}`
      };
    }
  }

  /**
   * Cleanup (soft by default, full on explicit request)
   */
  async cleanup(full: boolean = false): Promise<void> {
    // Flush any pending state saves before cleanup
    await this.flushStateSave();

    if (full) {
      if (this.page) await this.page.close();
      if (this.context) await this.context.close();
      if (this.browser) await this.browser.close();

      this.page = null;
      this.context = null;
      this.browser = null;
      this.currentUrl = null;

      console.error('🔌 Browser fully shut down');
    } else {
      // Soft cleanup - keep browser alive
      console.error('♻️  State saved, browser kept alive');
    }
  }
}
