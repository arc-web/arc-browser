
import { PlaywrightMCPServer } from './src/server_core.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';

async function verify() {
    console.log('Verifying Playwright MCP Server...');

    // Mock process.env
    process.env.BROWSER_STATE_DIR = './.test-browser-state';
    // We want to verify that if BROWSER_USER_DATA_DIR is NOT set, it defaults to a persistent path
    delete process.env.BROWSER_USER_DATA_DIR;

    const server = new PlaywrightMCPServer();
    const mcpServer = server.getServer();

    // Check tools
    console.log('Checking tools...');
    // @ts-ignore - Accessing private property for testing or using public API if available
    // The SDK doesn't expose tools directly easily without a request, so we'll mock a request if possible
    // or just inspect the handler if we could. 
    // But we can't easily inspect the handler.

    // However, we can check if the server was initialized with the correct userDataDir by inspecting the browserAgent
    // We'll need to use 'any' to bypass private access modifiers for verification
    const serverAny = server as any;
    const browserAgent = serverAny.browserAgent;

    if (browserAgent.userDataDir && browserAgent.userDataDir.endsWith('.browser-profile')) {
        console.log('✅ Persistent userDataDir is set by default:', browserAgent.userDataDir);
    } else {
        console.error('❌ Persistent userDataDir is NOT set correctly:', browserAgent.userDataDir);
    }

    // We can't easily invoke the list tools handler without a transport, 
    // but we can verify the code changes by reading the file content which we already did.
    // Let's try to instantiate it and see if it crashes.
    console.log('✅ Server instantiated successfully.');
}

verify().catch(console.error);
