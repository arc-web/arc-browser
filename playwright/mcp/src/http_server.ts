#!/usr/bin/env node

/**
 * HTTP/WebSocket Server for Playwright MCP
 * Enables remote access via HTTP (SSE) or WebSocket transports
 */

import express from 'express';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { SSEServerTransport } from '@modelcontextprotocol/sdk/server/sse.js';
import { PlaywrightMCPServer } from './server_core.js';
import * as http from 'http';
import type { Server as ExpressServer } from 'http';

export interface HTTPServerConfig {
  port?: number;
  corsOrigin?: string;
  apiKey?: string;
  transport?: 'sse' | 'streamable';
}

export class PlaywrightMCPHTTPServer {
  private app: express.Application;
  private server: ExpressServer | null = null;
  private config: Required<HTTPServerConfig>;
  private transports: Map<string, { transport: StreamableHTTPServerTransport | SSEServerTransport; server: PlaywrightMCPServer }> = new Map();

  constructor(config: HTTPServerConfig = {}) {
    this.config = {
      port: config.port || parseInt(process.env.MCP_PORT || '3000', 10),
      corsOrigin: config.corsOrigin || process.env.MCP_CORS_ORIGIN || '*',
      apiKey: config.apiKey || process.env.MCP_API_KEY || '',
      transport: config.transport || (process.env.MCP_TRANSPORT === 'sse' ? 'sse' : 'streamable')
    };

    this.app = express();
    this.setupMiddleware();
    this.setupRoutes();
  }

  private setupMiddleware(): void {
    // Security headers
    this.app.use((req, res, next) => {
      res.setHeader('X-Content-Type-Options', 'nosniff');
      res.setHeader('X-Frame-Options', 'DENY');
      res.setHeader('X-XSS-Protection', '1; mode=block');
      next();
    });

    // CORS configuration
    this.app.use((req, res, next) => {
      res.setHeader('Access-Control-Allow-Origin', this.config.corsOrigin);
      res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, Accept, mcp-session-id');
      res.setHeader('Access-Control-Max-Age', '86400');

      if (req.method === 'OPTIONS') {
        res.sendStatus(204);
        return;
      }
      next();
    });

    // Authentication middleware (if API key is set)
    if (this.config.apiKey) {
      this.app.use((req, res, next) => {
        const authHeader = req.headers.authorization;
        const apiKey = authHeader?.replace('Bearer ', '') || req.query.apiKey as string;

        if (apiKey !== this.config.apiKey) {
          res.status(401).json({
            jsonrpc: '2.0',
            error: {
              code: -32001,
              message: 'Unauthorized: Invalid API key'
            },
            id: null
          });
          return;
        }
        next();
      });
    }

    // Request logging
    this.app.use((req, res, next) => {
      console.error(`[HTTP] ${req.method} ${req.path}`);
      next();
    });
  }

  private setupRoutes(): void {
    // Health check endpoint
    this.app.get('/health', (req, res) => {
      res.json({
        status: 'ok',
        server: 'playwright-mcp',
        version: '1.0.0',
        transport: this.config.transport,
        timestamp: new Date().toISOString()
      });
    });

    // Tools list endpoint (alternative to MCP protocol)
    this.app.get('/tools', async (req, res) => {
      try {
        // Get tools from MCP server
        const tools = [
          {
            name: 'browser_execute',
            description: 'Execute browser automation tasks using natural language',
            parameters: {
              task: { type: 'string', required: true },
              url: { type: 'string', required: false },
              waitFor: { type: 'string', required: false },
              extract: { type: 'array', required: false },
              screenshot: { type: 'boolean', required: false }
            }
          },
          {
            name: 'browser_state',
            description: 'Manage browser state (cookies, localStorage, authentication)',
            parameters: {
              action: { type: 'string', enum: ['save', 'clear', 'status'], required: true }
            }
          }
        ];

        res.json({ tools });
      } catch (error) {
        res.status(500).json({
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    });

    // MCP protocol endpoint
    this.app.post('/mcp', async (req, res) => {
      const sessionId = req.headers['mcp-session-id'] as string || `session-${Date.now()}`;

      try {
        let session = this.transports.get(sessionId);

        if (!session) {
          // Create new MCP server instance for this session
          const mcpServer = new PlaywrightMCPServer();
          let transport: StreamableHTTPServerTransport | SSEServerTransport;

          if (this.config.transport === 'sse') {
            // SSE transport
            transport = new SSEServerTransport('/mcp', res);
          } else {
            // StreamableHTTP transport - takes options object
            transport = new StreamableHTTPServerTransport({
              sessionIdGenerator: () => sessionId
            });
          }

          await mcpServer.getServer().connect(transport);
          session = { transport, server: mcpServer };
          this.transports.set(sessionId, session);
          console.error(`[HTTP] New MCP session: ${sessionId}`);
        }

        // Handle the request
        if (session.transport instanceof StreamableHTTPServerTransport) {
          // StreamableHTTP transport handles requests via handleRequest
          await session.transport.handleRequest(req, res, undefined);
        } else {
          // SSE transport is already set up in GET /mcp endpoint
          // This POST endpoint shouldn't be used for SSE
          res.status(405).json({
            jsonrpc: '2.0',
            error: {
              code: -32601,
              message: 'SSE transport uses GET /mcp endpoint, not POST'
            },
            id: null
          });
        }
      } catch (error) {
        console.error(`[HTTP] Error handling MCP request:`, error);
        res.status(500).json({
          jsonrpc: '2.0',
          error: {
            code: -32603,
            message: error instanceof Error ? error.message : 'Internal error'
          },
            id: null
        });
      }
    });

    // SSE endpoint (GET /mcp for SSE connections)
    this.app.get('/mcp', async (req, res) => {
      const accept = req.headers.accept;

      if (accept && accept.includes('text/event-stream')) {
        const sessionId = req.headers['mcp-session-id'] as string || `session-${Date.now()}`;

        try {
          // Create new MCP server instance for this SSE session
          const mcpServer = new PlaywrightMCPServer();
          const transport = new SSEServerTransport('/mcp', res);
          await mcpServer.getServer().connect(transport);
          this.transports.set(sessionId, { transport, server: mcpServer });
          console.error(`[HTTP] SSE connection established: ${sessionId}`);
        } catch (error) {
          console.error(`[HTTP] SSE connection error:`, error);
          res.status(500).json({
            jsonrpc: '2.0',
            error: {
              code: -32603,
              message: 'Failed to establish SSE connection'
            },
            id: null
          });
        }
      } else {
        // Return server info
        res.json({
          name: 'playwright-mcp',
          version: '1.0.0',
          transport: this.config.transport,
          endpoints: {
            mcp: '/mcp',
            health: '/health',
            tools: '/tools'
          }
        });
      }
    });
  }

  async start(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.server = http.createServer(this.app);

      this.server.listen(this.config.port, () => {
        console.error('🚀 Playwright MCP HTTP Server running');
        console.error(`   Port: ${this.config.port}`);
        console.error(`   Transport: ${this.config.transport}`);
        console.error(`   CORS Origin: ${this.config.corsOrigin}`);
        console.error(`   Authentication: ${this.config.apiKey ? 'Enabled' : 'Disabled'}`);
        console.error(`   Health: http://localhost:${this.config.port}/health`);
        console.error(`   MCP Endpoint: http://localhost:${this.config.port}/mcp`);
        resolve();
      });

      this.server.on('error', (error: Error) => {
        console.error('[HTTP] Server error:', error);
        reject(error);
      });
    });
  }

  async stop(): Promise<void> {
    return new Promise((resolve) => {
      // Close all transports
      for (const session of this.transports.values()) {
        // Transport cleanup handled by SDK
        try {
          session.server.getServer().close();
        } catch (error) {
          // Ignore cleanup errors
        }
      }
      this.transports.clear();

      if (this.server) {
        this.server.close(() => {
          console.error('[HTTP] Server stopped');
          resolve();
        });
      } else {
        resolve();
      }
    });
  }
}
