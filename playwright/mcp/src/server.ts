#!/usr/bin/env node

/**
 * Playwright MCP Server Entry Point
 * Supports stdio (Cursor) and HTTP/WebSocket (remote) transports
 */

import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { PlaywrightMCPServer } from './server_core.js';
import { PlaywrightMCPHTTPServer } from './http_server.js';

// Determine transport mode from environment
const transportMode = process.env.MCP_TRANSPORT || 'stdio';

if (transportMode === 'http' || transportMode === 'websocket') {
  // HTTP/WebSocket mode for remote access
  const transportType = process.env.MCP_TRANSPORT_TYPE === 'sse' ? 'sse' : 'streamable';
  const httpServer = new PlaywrightMCPHTTPServer({
    port: parseInt(process.env.MCP_PORT || '3000', 10),
    corsOrigin: process.env.MCP_CORS_ORIGIN,
    apiKey: process.env.MCP_API_KEY,
    transport: transportType
  });

  httpServer.start().catch((error) => {
    console.error('Failed to start HTTP server:', error);
    process.exit(1);
  });

  // Graceful shutdown
  process.on('SIGTERM', async () => {
    await httpServer.stop();
    process.exit(0);
  });

  process.on('SIGINT', async () => {
    await httpServer.stop();
    process.exit(0);
  });
} else {
  // Stdio mode for Cursor
  const server = new PlaywrightMCPServer();
  const transport = new StdioServerTransport();

  server.getServer().connect(transport).then(() => {
    console.error('🚀 Playwright MCP Server running (stdio mode)');
    console.error('   State directory:', process.env.BROWSER_STATE_DIR || './.mcp-browser-state');
    console.error('   Headless:', process.env.HEADLESS !== 'false');
  }).catch((error) => {
    console.error('Failed to start server:', error);
    process.exit(1);
  });
}
