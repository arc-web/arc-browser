# Playwright Stealth Enhancement Guide

**Date**: 2025-01-25  
**Purpose**: Reduce bot detection and CAPTCHA challenges

---

## Overview

This guide documents techniques to make Playwright automation less detectable by bot detection systems. Based on GitHub best practices and real-world testing.

---

## Key Detection Methods

### 1. **Browser Fingerprinting**
- `navigator.webdriver` property
- Canvas fingerprinting
- WebGL fingerprinting
- Audio context fingerprinting
- Plugin enumeration
- Hardware concurrency
- Device memory
- Screen resolution/color depth

### 2. **Behavioral Patterns**
- Perfect timing (no human-like delays)
- Instant mouse movements
- Perfect typing speed
- No mouse acceleration curves
- No random pauses

### 3. **Browser Signatures**
- Missing `window.chrome` object
- Automation flags in launch args
- Missing browser extensions
- Suspicious user agent strings
- Missing or incorrect headers

### 4. **Network Patterns**
- IP reputation
- Request timing patterns
- Missing or incorrect TLS fingerprint
- Suspicious cookie patterns

---

## Enhancement Techniques

### ✅ Already Implemented

1. **Core Stealth Script** (`injectStealthScript`)
   - Hides `navigator.webdriver`
   - Canvas/WebGL/Audio fingerprinting protection
   - Chrome object simulation
   - Plugin simulation
   - Hardware concurrency masking

2. **Launch Arguments**
   - `--disable-blink-features=AutomationControlled`
   - Various Chrome flags to reduce detection

3. **State Persistence**
   - Persistent cookies/sessions
   - Maintains login state

4. **Rate Limiting**
   - 300ms minimum between actions
   - Prevents rapid-fire automation

### 🆕 Recommended Enhancements

#### 1. **Enhanced Launch Arguments**

Add these additional flags to reduce detection:

```typescript
args: [
  // Core stealth
  '--disable-blink-features=AutomationControlled',
  
  // Remove automation indicators
  '--disable-dev-shm-usage',
  '--no-sandbox',
  '--disable-setuid-sandbox',
  
  // Make it look like a real browser
  '--disable-infobars',
  '--disable-notifications',
  '--disable-popup-blocking',
  '--disable-translate',
  
  // Performance flags that also help stealth
  '--disable-background-timer-throttling',
  '--disable-backgrounding-occluded-windows',
  '--disable-renderer-backgrounding',
  
  // NEW: Additional stealth flags
  '--disable-features=IsolateOrigins,site-per-process,AutomationControlled',
  '--disable-site-isolation-trials',
  '--disable-ipc-flooding-protection',
  '--disable-component-extensions-with-background-pages',
  '--disable-default-apps',
  '--disable-extensions-file-access-check',
  '--disable-extensions-http-throttling',
  
  // Make browser look more legitimate
  '--enable-features=NetworkService,NetworkServiceInProcess',
  '--force-color-profile=srgb',
  '--metrics-recording-only',
  '--use-mock-keychain',
  
  // NEW: Additional stealth
  '--disable-sync',
  '--disable-features=TranslateUI,BlinkGenPropertyTrees',
  '--disable-component-update',
  '--no-default-browser-check',
  '--no-first-run',
  '--password-store=basic',
  
  // NEW: WebRTC and privacy
  '--disable-webrtc',
  '--disable-webrtc-hw-encoding',
  '--disable-webrtc-hw-decoding',
]
```

#### 2. **Enhanced Stealth Script**

Add these additional protections:

```javascript
// NEW: Hide automation in window object
Object.defineProperty(window, 'navigator', {
  value: new Proxy(navigator, {
    has: (target, key) => (key === 'webdriver' ? false : key in target),
    get: (target, key) => {
      if (key === 'webdriver') return false;
      if (key === 'plugins') {
        // Return realistic plugins array
        return [/* plugins */];
      }
      if (key === 'languages') {
        return ['en-US', 'en'];
      }
      return target[key];
    }
  })
});

// NEW: Override toString methods
const originalToString = Function.prototype.toString;
Function.prototype.toString = function() {
  if (this === navigator.webdriver) {
    return 'function webdriver() { [native code] }';
  }
  return originalToString.call(this);
};

// NEW: Hide automation in document
Object.defineProperty(document, '$cdc_asdjflasutopfhvcZLmcfl_', {
  get: () => undefined,
  configurable: true
});

Object.defineProperty(document, '$chrome_asyncScriptInfo', {
  get: () => undefined,
  configurable: true
});

// NEW: Override permissions.query to be more realistic
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
  parameters.name === 'notifications' ?
    Promise.resolve({ state: Notification.permission }) :
    originalQuery(parameters)
);

// NEW: Add realistic battery API
if (navigator.getBattery) {
  const originalGetBattery = navigator.getBattery;
  navigator.getBattery = function() {
    return originalGetBattery.call(this).then(battery => {
      // Add slight randomization to battery level
      Object.defineProperty(battery, 'level', {
        get: () => Math.min(1, Math.max(0, 0.8 + Math.random() * 0.2))
      });
      return battery;
    });
  };
}

// NEW: Override Notification.permission
Object.defineProperty(Notification, 'permission', {
  get: () => 'default'
});

// NEW: Add realistic media devices
if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
  const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices;
  navigator.mediaDevices.enumerateDevices = function() {
    return originalEnumerateDevices.call(this).then(devices => {
      // Add slight randomization to device IDs
      return devices.map(device => ({
        ...device,
        deviceId: device.deviceId + Math.random().toString(36).substring(7)
      }));
    });
  };
}
```

#### 3. **User Agent Rotation**

Rotate user agents to avoid fingerprinting:

```typescript
const USER_AGENTS = [
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
];

// Use a consistent user agent per session
const userAgent = USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
```

#### 4. **Behavioral Enhancements**

Add human-like behaviors:

```typescript
// Add random delays between actions
async function humanDelay(min = 100, max = 500) {
  const delay = Math.floor(Math.random() * (max - min + 1)) + min;
  await new Promise(resolve => setTimeout(resolve, delay));
}

// Human-like mouse movements
async function humanMouseMove(page: Page, from: {x: number, y: number}, to: {x: number, y: number}) {
  const steps = 10 + Math.floor(Math.random() * 10);
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    // Bezier curve for natural movement
    const x = from.x + (to.x - from.x) * t;
    const y = from.y + (to.y - from.y) * t;
    await page.mouse.move(x, y);
    await new Promise(resolve => setTimeout(resolve, 10 + Math.random() * 20));
  }
}

// Human-like typing
async function humanType(page: Page, selector: string, text: string) {
  await page.focus(selector);
  for (const char of text) {
    await page.keyboard.type(char, { delay: 50 + Math.random() * 100 });
    // Occasional longer pauses (like thinking)
    if (Math.random() < 0.1) {
      await new Promise(resolve => setTimeout(resolve, 200 + Math.random() * 300));
    }
  }
}
```

#### 5. **Viewport Randomization**

Slightly randomize viewport to avoid fingerprinting:

```typescript
const viewports = [
  { width: 1920, height: 1080 },
  { width: 1366, height: 768 },
  { width: 1440, height: 900 },
  { width: 1536, height: 864 },
];

const viewport = viewports[Math.floor(Math.random() * viewports.length)];
```

#### 6. **Headers Enhancement**

Add more realistic headers:

```typescript
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
  'Cache-Control': 'max-age=0',
}
```

---

## GitHub Best Practices

### Popular Libraries

1. **playwright-extra + puppeteer-extra-plugin-stealth**
   - Most popular solution
   - Comprehensive stealth features
   - Actively maintained

2. **rebrowser-patches**
   - Collection of patches for Playwright/Puppeteer
   - Specifically targets Cloudflare and DataDome
   - Easy to apply/remove

3. **Botright**
   - Advanced framework built on Playwright
   - Includes fingerprint-changing
   - AI-powered CAPTCHA solving

### Common Patterns

1. **Always use persistent context** (you're already doing this ✅)
2. **Never use headless mode** for sensitive sites (you're configurable ✅)
3. **Rotate user agents** per session
4. **Add random delays** between actions
5. **Use residential proxies** for IP rotation
6. **Maintain session state** (cookies, localStorage)

---

## Testing Stealth Effectiveness

### Test Sites

1. **Bot Detection Test Sites**:
   - https://bot.sannysoft.com/
   - https://arh.antoinevastel.com/bots/areyouheadless
   - https://pixelscan.net/

2. **CAPTCHA Providers**:
   - Google reCAPTCHA
   - hCaptcha
   - Cloudflare Turnstile

### What to Check

1. `navigator.webdriver` should be `undefined` or `false`
2. Canvas fingerprint should vary slightly
3. WebGL renderer should be realistic
4. Plugins array should contain Chrome plugins
5. `window.chrome` should exist
6. No automation flags in console

---

## Implementation Priority

### High Priority (Do First)
1. ✅ Enhanced launch arguments
2. ✅ Enhanced stealth script (document.$cdc_*, toString overrides)
3. ✅ Better headers (Sec-Ch-Ua headers)
4. ✅ User agent rotation

### Medium Priority
5. ⚠️ Behavioral enhancements (mouse movements, typing)
6. ⚠️ Viewport randomization
7. ⚠️ Battery API override

### Low Priority (Nice to Have)
8. 💡 Proxy rotation
9. 💡 CAPTCHA solving integration
10. 💡 Advanced fingerprint randomization

---

## Additional Resources

- [Playwright Stealth Plugin](https://github.com/berstend/puppeteer-extra/tree/master/packages/puppeteer-extra-plugin-stealth)
- [Rebrowser Patches](https://github.com/rebrowser/rebrowser-patches)
- [Botright Framework](https://github.com/Vinyzu/Botright)
- [Browser Fingerprinting Guide](https://fingerprint.com/blog/browser-fingerprinting-techniques/)

---

## Notes

- **Don't over-optimize**: Too much randomization can also look suspicious
- **Test incrementally**: Add one enhancement at a time and test
- **Monitor success rates**: Track CAPTCHA frequency before/after changes
- **Keep user agent updated**: Use recent Chrome versions
- **Maintain consistency**: Use same fingerprint within a session

