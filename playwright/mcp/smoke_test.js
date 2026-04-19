#!/usr/bin/env node

/**
 * Playwright MCP Smoke Test
 * Tests server configuration, connectivity, and basic functionality
 */

import { spawn } from 'child_process';
import { readFileSync, existsSync, mkdirSync, writeFileSync, unlinkSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Test configuration
const SERVER_PATH = join(__dirname, 'dist', 'server.js');
const TIMEOUT = 10000; // 10 seconds

// Test results
const results = {
  total: 0,
  passed: 0,
  failed: 0,
  skipped: 0,
  tests: []
};

// Colors for output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function test(name, fn) {
  results.total++;
  const testName = name;

  try {
    const result = fn();
    if (result instanceof Promise) {
      return result.then(
        (success) => {
          if (success) {
            results.passed++;
            results.tests.push({ name: testName, status: 'PASS' });
            log(`✅ ${testName}`, 'green');
            return true;
          } else {
            results.failed++;
            results.tests.push({ name: testName, status: 'FAIL' });
            log(`❌ ${testName}`, 'red');
            return false;
          }
        },
        (error) => {
          results.failed++;
          results.tests.push({ name: testName, status: 'FAIL', error: error.message });
          log(`❌ ${testName}: ${error.message}`, 'red');
          return false;
        }
      );
    } else {
      if (result) {
        results.passed++;
        results.tests.push({ name: testName, status: 'PASS' });
        log(`✅ ${testName}`, 'green');
        return true;
      } else {
        results.failed++;
        results.tests.push({ name: testName, status: 'FAIL' });
        log(`❌ ${testName}`, 'red');
        return false;
      }
    }
  } catch (error) {
    results.failed++;
    results.tests.push({ name: testName, status: 'FAIL', error: error.message });
    log(`❌ ${testName}: ${error.message}`, 'red');
    return false;
  }
}

// Test 1: Server binary exists
function testServerBinary() {
  return test('Server binary exists', () => {
    try {
      return existsSync(SERVER_PATH);
    } catch {
      return false;
    }
  });
}

// Test 2: Package.json valid
function testPackageJson() {
  return test('Package.json is valid', () => {
    try {
      const packagePath = join(__dirname, 'package.json');
      const pkg = JSON.parse(readFileSync(packagePath, 'utf-8'));
      return pkg.name && pkg.version && pkg.dependencies;
    } catch {
      return false;
    }
  });
}

// Test 3: Dependencies installed
function testDependencies() {
  return test('Dependencies installed', () => {
    try {
      const nodeModulesPath = join(__dirname, 'node_modules');
      return existsSync(nodeModulesPath);
    } catch {
      return false;
    }
  });
}

// Test 4: Server starts without errors
function testServerStartup() {
  return test('Server starts without errors', async () => {
    return new Promise((resolve) => {
      const server = spawn('node', [SERVER_PATH], {
        env: {
          ...process.env,
          BROWSER_STATE_DIR: join(__dirname, '.test-browser-state'),
          HEADLESS: 'true'
        },
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stderrOutput = '';
      let startupSuccess = false;

      const timeout = setTimeout(() => {
        server.kill();
        resolve(false);
      }, 3000);

      server.stderr.on('data', (data) => {
        stderrOutput += data.toString();
        if (stderrOutput.includes('Playwright MCP Server running')) {
          startupSuccess = true;
          clearTimeout(timeout);
          server.kill();
          resolve(true);
        }
      });

      server.on('error', () => {
        clearTimeout(timeout);
        resolve(false);
      });

      server.on('exit', () => {
        clearTimeout(timeout);
        if (!startupSuccess) {
          resolve(false);
        }
      });
    });
  });
}

// Test 5: MCP Protocol - Initialize
function testMCPInitialize() {
  return test('MCP Protocol - Initialize handshake', async () => {
    return new Promise((resolve) => {
      const server = spawn('node', [SERVER_PATH], {
        env: {
          ...process.env,
          BROWSER_STATE_DIR: join(__dirname, '.test-browser-state'),
          HEADLESS: 'true'
        },
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stdoutOutput = '';
      let initSuccess = false;

      const timeout = setTimeout(() => {
        server.kill();
        resolve(false);
      }, TIMEOUT);

      // Send initialize request
      const initRequest = {
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: {
            name: 'smoke-test',
            version: '1.0.0'
          }
        }
      };

      server.stdout.on('data', (data) => {
        stdoutOutput += data.toString();
        try {
          const lines = stdoutOutput.split('\n').filter(l => l.trim());
          for (const line of lines) {
            const response = JSON.parse(line);
            if (response.id === 1 && response.result) {
              initSuccess = true;
              clearTimeout(timeout);
              server.kill();
              resolve(true);
            }
          }
        } catch (e) {
          // Not JSON yet, continue waiting
        }
      });

      server.on('error', () => {
        clearTimeout(timeout);
        resolve(false);
      });

      setTimeout(() => {
        server.stdin.write(JSON.stringify(initRequest) + '\n');
      }, 500);

      server.on('exit', () => {
        clearTimeout(timeout);
        if (!initSuccess) {
          resolve(false);
        }
      });
    });
  });
}

// Test 6: MCP Protocol - List Tools
function testMCPListTools() {
  return test('MCP Protocol - List tools', async () => {
    return new Promise((resolve) => {
      const server = spawn('node', [SERVER_PATH], {
        env: {
          ...process.env,
          BROWSER_STATE_DIR: join(__dirname, '.test-browser-state'),
          HEADLESS: 'true'
        },
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stdoutOutput = '';
      let toolsFound = false;

      const timeout = setTimeout(() => {
        server.kill();
        resolve(false);
      }, TIMEOUT);

      // Send initialize then list tools
      const initRequest = {
        jsonrpc: '2.0',
        id: 1,
        method: 'initialize',
        params: {
          protocolVersion: '2024-11-05',
          capabilities: {},
          clientInfo: { name: 'smoke-test', version: '1.0.0' }
        }
      };

      const listToolsRequest = {
        jsonrpc: '2.0',
        id: 2,
        method: 'tools/list',
        params: {}
      };

      server.stdout.on('data', (data) => {
        stdoutOutput += data.toString();
        try {
          const lines = stdoutOutput.split('\n').filter(l => l.trim());
          for (const line of lines) {
            const response = JSON.parse(line);
            if (response.id === 2 && response.result && response.result.tools) {
              const tools = response.result.tools;
              if (tools.some(t => t.name === 'browser_execute') &&
                  tools.some(t => t.name === 'browser_state')) {
                toolsFound = true;
                clearTimeout(timeout);
                server.kill();
                resolve(true);
              }
            }
          }
        } catch (e) {
          // Not JSON yet, continue waiting
        }
      });

      setTimeout(() => {
        server.stdin.write(JSON.stringify(initRequest) + '\n');
        setTimeout(() => {
          server.stdin.write(JSON.stringify(listToolsRequest) + '\n');
        }, 500);
      }, 500);

      server.on('error', () => {
        clearTimeout(timeout);
        resolve(false);
      });

      server.on('exit', () => {
        clearTimeout(timeout);
        if (!toolsFound) {
          resolve(false);
        }
      });
    });
  });
}

// Test 7: Browser state directory
function testBrowserStateDir() {
  return test('Browser state directory accessible', () => {
    try {
      const stateDir = process.env.BROWSER_STATE_DIR || join(__dirname, '.test-browser-state');

      // Try to create directory if it doesn't exist
      if (!existsSync(stateDir)) {
        mkdirSync(stateDir, { recursive: true });
      }

      // Try to write a test file
      const testFile = join(stateDir, '.test-write');
      writeFileSync(testFile, 'test');
      unlinkSync(testFile);

      return true;
    } catch {
      return false;
    }
  });
}

// Test 8: Playwright available
function testPlaywrightAvailable() {
  return test('Playwright CLI available', async () => {
    return new Promise((resolve) => {
      const proc = spawn('npx', ['playwright', '--version'], {
        cwd: __dirname,
        stdio: 'pipe'
      });

      let output = '';
      proc.stdout.on('data', (data) => {
        output += data.toString();
      });

      proc.on('close', (code) => {
        resolve(code === 0 && output.includes('Version'));
      });

      proc.on('error', () => {
        resolve(false);
      });
    });
  });
}

// Main test runner
async function runTests() {
  log('\n' + '='.repeat(60), 'cyan');
  log('Playwright MCP Smoke Test', 'cyan');
  log('='.repeat(60) + '\n', 'cyan');

  log('Running smoke tests...\n', 'blue');

  // Run all tests
  await testServerBinary();
  await testPackageJson();
  await testDependencies();
  await testBrowserStateDir();
  await testPlaywrightAvailable();
  await testServerStartup();
  await testMCPInitialize();
  await testMCPListTools();

  // Summary
  log('\n' + '='.repeat(60), 'cyan');
  log('Test Summary', 'cyan');
  log('='.repeat(60), 'cyan');
  log(`Total:  ${results.total}`, 'blue');
  log(`Passed: ${results.passed}`, 'green');
  log(`Failed: ${results.failed}`, results.failed > 0 ? 'red' : 'reset');
  log(`Skipped: ${results.skipped}`, 'yellow');
  log('='.repeat(60) + '\n', 'cyan');

  // Detailed results
  if (results.failed > 0) {
    log('Failed Tests:', 'red');
    results.tests
      .filter(t => t.status === 'FAIL')
      .forEach(t => {
        log(`  - ${t.name}`, 'red');
        if (t.error) {
          log(`    Error: ${t.error}`, 'red');
        }
      });
    log('');
  }

  // Exit code
  process.exit(results.failed > 0 ? 1 : 0);
}

// Run tests
runTests().catch((error) => {
  log(`\n❌ Test runner error: ${error.message}`, 'red');
  process.exit(1);
});
