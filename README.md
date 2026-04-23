# ARC Browser

A stealth browser automation agent that gives Claude Code (or any MCP client) real browser control through natural language. Not another Puppeteer wrapper - ARC Browser is an MCP server with anti-detection, session persistence, concurrent multi-site operation, and human-like interaction baked in.

## What makes this different

| Feature | ARC Browser | Playwright MCP | Browser-use alone | Stagehand |
|---------|------------|----------------|-------------------|-----------|
| Anti-detection (stealth patches) | Yes (Patchright + playwright-stealth) | No | Partial | No |
| Human-like timing (Bezier curves, log-normal delays) | Yes | No | No | No |
| Persistent sessions (survives restarts) | Yes (Chrome profiles per session) | No | No | No |
| Concurrent multi-site sessions | Yes (session pool) | No | No | No |
| Risk-aware routing (mode per domain) | Yes (site registry) | No | No | No |
| Rate limiting per domain | Yes | No | No | No |
| Autonomous multi-step tasks (local LLM) | Yes (Ollama) | No | Yes (requires cloud LLM) | Yes (requires cloud LLM) |
| Second monitor placement | Yes (auto-detect) | No | No | No |
| 1Password credential integration | Yes | No | No | No |
| MCP native (works with Claude Code) | Yes | Yes | No | No |

## Architecture

```
                          Claude Code / MCP Client
                                    |
                                    | stdio
                                    v
                        +-------------------+
                        |    server.py      |
                        |  (FastMCP server) |
                        |  Rate limiter     |
                        |  16 tool endpoints|
                        +--------+----------+
                                 |
                    +------------+------------+
                    |                         |
            +-------+-------+        +-------+-------+
            |   router.py   |        |   agent.py    |
            | URL classifier|        | Autonomous    |
            | Risk/mode/rate|        | browser-use + |
            | Site registry |        | Ollama LLM    |
            +-------+-------+        +-------+-------+
                    |                         |
                    v                         v
            +-------+-------------------------+-------+
            |              browser.py                  |
            |          Session Pool Manager            |
            |  +----------+  +----------+  +--------+ |
            |  | session:  |  | session:  |  | session:| |
            |  | "skool"  |  | "default" |  | "test" | |
            |  | (headed) |  | (headless)|  | (headed)| |
            |  +----------+  +----------+  +--------+ |
            +------------------------------------------+
                    |
        +-----------+-----------+
        |           |           |
   +----+----+ +----+----+ +---+-----+
   |Patchright| |Stealth  | |HumanCur.|
   |Chromium  | |Patches  | |Bezier   |
   |(per mode)| |(auto)   | |movement |
   +----------+ +---------+ +---------+
```

## Browser Modes

ARC Browser picks the right execution mode per-site based on risk, detection sensitivity, and stealth requirements.

```
  URL arrives
      |
      v
  router.py classifies domain
      |
      +-- site_registry.json match? ---> use registered mode + rate limit
      |
      +-- CDP-required site? ----------> cdp mode (LinkedIn, Twitter, Facebook)
      |       |
      |       +-- user must call browser_task_confirmed()
      |       +-- connects to real Chrome at ws://localhost:9222
      |       +-- most stealthy (real browser fingerprint)
      |       +-- disruptive (takes over user's Chrome)
      |
      +-- needs extensions? -----------> headed mode
      |
      +-- low risk? -------------------> headless mode
      |       |
      |       +-- fastest, no window
      |       +-- stealth patches still applied
      |       +-- good for scraping, data extraction
      |
      +-- default ----------------------> headed mode
              |
              +-- Patchright + stealth on second monitor
              +-- visible window at 1920x1080
              +-- human-like delays on all interactions
              +-- session persisted to disk (cookies survive restart)
```

### Mode decision matrix

| Mode | Window | Stealth | Session | Use when |
|------|--------|---------|---------|----------|
| **headed** | Yes (monitor 2) | Patchright + playwright-stealth + HumanCursor | Persistent Chrome profile | Default. Sites that check for bot behavior but don't require real Chrome |
| **headless** | No | Patchright + basic flags | Persistent Chrome profile | Low-risk sites (GitHub, docs). Speed over stealth |
| **cdp** | User's Chrome | Real browser (maximum stealth) | User's existing profile | High-detection sites (LinkedIn, Twitter, Facebook). Disruptive - takes over browser |
| **vps** | Remote | Browserless instance | Ephemeral | Remote execution, IP rotation, geographic targeting |

## Session Pool

ARC Browser runs multiple browser sessions concurrently. Each session is an independent Chrome instance with its own profile, cookies, and state.

```
Session Pool (_sessions dict)
    |
    +-- "skool"   --> BrowserContext (headed, Skool cookies, logged in)
    |                  +-- Page 0: skool.com/stackpack/about
    |                  +-- Page 1: skool.com/stackpack/classroom
    |
    +-- "default" --> BrowserContext (headless, clean profile)
    |                  +-- Page 0: github.com/arc-web/...
    |
    +-- "client1" --> BrowserContext (headed, client dashboard)
                       +-- Page 0: app.example.com/dashboard
```

Sessions are:
- **Persistent**: Chrome profile saved to `sessions/<name>/`. Cookies, localStorage, and auth survive server restarts.
- **Isolated**: Each session is a separate Chromium process. No cookie leakage between sessions.
- **Concurrent**: Multiple sessions active simultaneously. Skool scan + GitHub check + client dashboard all at once.
- **Self-healing**: Stale `SingletonLock` files from crashed Chrome processes are auto-detected and cleaned up.

## Rate Limiting

Per-domain rolling window (1 hour). Configured in `site_registry.json`:

```json
{
  "skool.com":    { "risk": "low",  "mode": "headed",   "actions_per_hour": 40 },
  "linkedin.com": { "risk": "high", "mode": "cdp",      "actions_per_hour": 15 },
  "github.com":   { "risk": "low",  "mode": "headless", "actions_per_hour": 60 }
}
```

Unknown domains default to 25 actions/hour in headed mode.

## Human-Like Interaction

Every click, type, and navigation includes realistic human behavior:

```
Click flow:
  1. Locate element bounding box
  2. Generate Bezier curve from current cursor position (HumanCursor)
  3. Move mouse along curve with variable speed
  4. Pause 80-200ms (hover delay)
  5. Click

Type flow:
  1. Click target field
  2. Pause 300-700ms (thinking delay)
  3. Type each character with 70-180ms gaps (variable per-character)

Navigation delay:
  1. Page loads (domcontentloaded)
  2. Log-normal delay 1.0-2.5s (simulates reading/orienting)

All delays use log-normal distribution - clusters around the mean
with occasional longer pauses, matching real human timing patterns.
```

## Tech Stack

| Layer | Technology | Version | Why |
|-------|-----------|---------|-----|
| MCP Server | FastMCP (mcp SDK) | 1.26.0 | Native Claude Code integration, stdio transport |
| Browser Engine | Patchright | 1.58.0 | Playwright fork with automation detection bypasses baked into the Chromium binary |
| Stealth | tf-playwright-stealth | 1.2.0 | Runtime JS patches: navigator.webdriver, chrome.runtime, permissions, plugins, languages, WebGL |
| Cursor | HumanCursor | 1.1.5 | Bezier curve mouse trajectories. Falls back to random-point-in-bbox if unavailable |
| Autonomous Agent | browser-use | 0.12.6 | Multi-step task execution with vision + DOM understanding |
| Local LLM | Ollama (qwen2.5:14b) | - | Powers autonomous tasks without cloud API calls. Runs entirely on-device |
| Credentials | 1Password CLI (op) | - | Zero hardcoded secrets. All creds fetched at runtime from vault |
| Runtime | Python | 3.14+ | Async-native with asyncio throughout |

## MCP Tools

| Tool | Session-aware | Description |
|------|:---:|-------------|
| `browser_task` | Yes | Autonomous natural language task (router picks mode) |
| `browser_task_confirmed` | Yes | Autonomous task for CDP-required sites (explicit opt-in) |
| `browser_navigate` | Yes | Navigate to URL |
| `browser_evaluate` | Yes | Execute JavaScript, return result |
| `browser_click` | Yes | Click element (CSS selector, human-like) |
| `browser_type` | Yes | Type into field (human-like per-char timing) |
| `browser_wait` | Yes | Wait for element to appear |
| `browser_screenshot` | Yes | Capture page as base64 PNG |
| `browser_snapshot` | Yes | Accessibility tree (structured, low-token) |
| `browser_preflight` | No | Preview mode/risk/rate for a URL |
| `browser_skool_setup` | - | One-time Skool login (manual CAPTCHA) |
| `browser_skool_setup_done` | - | Save Skool session after login |

Every session-aware tool accepts `session: str = "default"`.

## Use Cases

### Skool Group Auditing
Scan any Skool community: member counts, admin roster, classroom courses, full feed extraction, zero-reply detection, admin response coverage. Persistent `skool` session means login once, scan forever.

### Multi-Site Monitoring
Run concurrent sessions against different platforms. Check client dashboards, competitor sites, and internal tools simultaneously without context switching or lock conflicts.

### Stealth Data Extraction
Sites that block Playwright/Puppeteer work fine with Patchright's patched Chromium + stealth JS patches + human-like timing. No detectable `navigator.webdriver`, no automation flags.

### Autonomous Browsing
Describe a task in natural language. The browser-use agent + local Ollama model handles multi-step workflows: navigate, read, click, fill forms, extract data - up to 25 steps per task with no cloud API calls.

### CDP Bridge for High-Detection Sites
LinkedIn, Twitter, Facebook - sites that detect even Patchright. Connect to the user's real Chrome instance via CDP. Maximum stealth at the cost of being disruptive (takes over the browser).

## Setup

```bash
# Clone
git clone https://github.com/arc-web/arc-browser.git
cd arc-browser

# Install dependencies
pip install -r requirements.txt

# Install Chromium for Patchright
python -m patchright install chromium

# Copy and configure environment
cp .env.example .env

# Register as MCP server in Claude Code
claude mcp add arc-browser "python3 $(pwd)/arc_browser/server.py"
```

### Optional: Ollama for autonomous tasks
```bash
# Install Ollama (macOS)
brew install ollama

# Pull the default model
ollama pull qwen2.5:14b
```

### Optional: VPS mode
Set `VPS_BROWSERLESS_URL` in `.env` to a Browserless instance endpoint for remote execution.

## When NOT to use arc-browser

- **One-shot HTTP scraping against a Cloudflare-protected endpoint**: use FlareSolverr on VPS Alpha (`http://187.77.222.191:8191/v1`). Arc-browser is optimized for interactive sessions; FlareSolverr returns HTML + `cf_clearance` cookies in a single POST so any HTTP client can continue from there. Docs: `~/ai/infra/paperclip/docs/flaresolverr.md`.
- **Trivial unauthenticated GETs** where `curl` or `requests` works: no reason to spin up Chromium.

## Project Structure

```
arc-browser/
  arc_browser/              # MCP server (generic browser tools)
    server.py               # 16 MCP tools: browser_* + skool_*
    browser.py              # Session pool, context factory, stealth
    agent.py                # Autonomous browser-use + Ollama
    router.py               # URL classifier (domain -> mode/risk/rate)
    config/
      settings.py           # Paths, env vars, monitor detection
      site_registry.json    # Per-domain config (incl. Skool, GitHub auth recipes)
    utils/
      human.py              # Bezier clicks, log-normal delays, human typing
      credentials.py        # 1Password CLI integration
  browser/                  # Skool-tuned browser primitives (used by scripts/)
  skool/                    # Skool scanner, gap analysis, HTML report generator
    scanner.py              # Extracts all Skool sections via JS evaluation
    paginator.py            # Scroll-until-stable helpers
    gap.py                  # 21-feature gap analysis matrix
    report.py               # Dark-themed HTML audit report
  scripts/                  # CLI tools for Skool auditing
    collect.py              # Full autonomous scan (no AI needed)
    onboard.py              # Admin access verification
    interpret.py            # Claude Code handoff for narratives
    deliver.py              # Render interpreted scan to HTML
    run_scan.py             # Quick CLI for reports from baseline data
  playwright/               # Legacy TypeScript Playwright MCP (reference)
    mcp/                    # Intent parser, stealth engine, HTTP transport
    agent/                  # EventEmitter-based autonomous agent
  app_integrations/         # Provider-specific browser recipes
  examples/                 # Baseline scan data, sample reports
  templates/                # Report CSS templates
  sessions/                 # Persistent Chrome profiles (gitignored)
  docs/
  requirements.txt
  .env.example
```

## License

Private - ARC Web
