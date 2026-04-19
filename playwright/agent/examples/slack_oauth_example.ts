/**
 * Example: Using Browser Automation Agent for Slack OAuth Setup
 *
 * This demonstrates the real-time feedback and insight generation
 * during autonomous task execution.
 */

import { browser_automation_agent } from '../browser_automation_agent';
import type { AgentTask, AgentStatus, AgentInsight } from '../types';

/**
 * Example 1: Simple task execution with console feedback
 */
async function simpleSlackOAuthSetup() {
  console.log('🚀 Starting Slack OAuth Setup Example\n');

  // Create agent
  const agent = new browser_automation_agent('example-agent-001');

  // Set up real-time feedback listeners
  agent.on('status', (status: AgentStatus) => {
    console.log(`[STATUS] ${status.message}`);

    if (status.progress) {
      const progressBar = createProgressBar(status.progress.percentage);
      console.log(`${progressBar} ${status.progress.percentage}%`);
    }
  });

  agent.on('insight', (insight: AgentInsight) => {
    console.log(`[INSIGHT] ${insight.message}`);

    if (insight.data) {
      console.log('         Data:', JSON.stringify(insight.data, null, 2));
    }

    if (insight.actionable) {
      console.log(`         💡 Suggested action: ${insight.suggestedAction}`);
    }
  });

  // Define the task
  const task: AgentTask = {
    id: 'task-001',
    description: 'Set up Slack OAuth scopes for MCP integration',
    params: {
      appId: process.env.SLACK_APP_ID || 'A09SMEFF7KR',
      scopes: [
        'channels:history',
        'channels:read',
        'chat:write',
        'reactions:write',
        'users:read',
        'users.profile:read'
      ]
    },
    browserOptions: {
      headless: false,
      slowMo: 100
    },
    priority: 'high',
    createdAt: new Date().toISOString()
  };

  // Execute task
  try {
    const result = await agent.executeTask(task);

    console.log('\n✅ Task Completed!');
    console.log('   Success:', result.success);
    console.log('   Execution Time:', `${result.executionTime}ms`);
    console.log('   Scopes Configured:', result.data?.scopesConfigured);

    // Show metrics
    const context = agent.getContext();
    console.log('\n📊 Agent Metrics:');
    console.log('   Tasks Completed:', context.metrics.tasksCompleted);
    console.log('   Success Rate:', `${(context.metrics.successRate * 100).toFixed(1)}%`);
    console.log('   Average Execution Time:', `${context.metrics.averageExecutionTime}ms`);

  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('\n❌ Task Failed:', errorMessage);
  } finally {
    await agent.cleanup();
  }
}

/**
 * Example 2: Natural language task with conversational feedback
 */
async function conversationalSlackSetup() {
  console.log('💬 Conversational Task Execution Example\n');

  const agent = new browser_automation_agent('conversational-agent');

  // Create a conversational feedback handler
  const conversationLog: string[] = [];

  agent.on('status', (status: AgentStatus) => {
    const message = formatConversationalMessage('status', status.message);
    console.log(message);
    conversationLog.push(message);
  });

  agent.on('insight', (insight: AgentInsight) => {
    const message = formatConversationalMessage('insight', insight.message);
    console.log(message);
    conversationLog.push(message);

    // Simulate interactive checkpoints
    if (insight.actionable && insight.suggestedAction) {
      console.log('\n💭 [AGENT] Would you like me to proceed with this action?');
      console.log(`   Suggested: ${insight.suggestedAction}`);
      console.log('   (In production, this would wait for user input)\n');
    }
  });

  // Natural language task description
  const task: AgentTask = {
    id: 'conversational-task-001',
    description: 'Please set up my Slack app with all the OAuth scopes we need',
    params: {
      appId: 'A09SMEFF7KR'
    },
    priority: 'high',
    createdAt: new Date().toISOString()
  };

  try {
    const result = await agent.executeTask(task);

    console.log('\n🎉 [AGENT] All done! Here\'s what I accomplished:');
    console.log(`   ✓ Configured ${result.data?.scopesConfigured} OAuth scopes`);
    console.log(`   ✓ Completed in ${(result.executionTime / 1000).toFixed(1)} seconds`);
    console.log('\n   💡 Your Slack app is now ready for the MCP integration!');

    // Save conversation log
    console.log('\n📝 Full conversation log saved to memory');

  } finally {
    await agent.cleanup();
  }
}

/**
 * Example 3: Multi-task workflow with learning
 */
async function multiTaskWorkflow() {
  console.log('🔄 Multi-Task Workflow Example\n');

  const agent = new browser_automation_agent('workflow-agent');

  // Track insights for learning
  const insights: AgentInsight[] = [];

  agent.on('insight', (insight: AgentInsight) => {
    insights.push(insight);
    console.log(`💡 ${insight.message}`);
  });

  agent.on('status', (status: AgentStatus) => {
    console.log(`📍 ${status.message}`);
  });

  // Task 1: Set up OAuth scopes
  console.log('\n=== Task 1: OAuth Setup ===');
  const task1: AgentTask = {
    id: 'workflow-task-001',
    description: 'Configure Slack OAuth scopes',
    params: { appId: 'A09SMEFF7KR' },
    createdAt: new Date().toISOString()
  };

  const result1 = await agent.executeTask(task1);

  if (result1.success) {
    console.log('✅ OAuth scopes configured\n');

    // Show what the agent learned
    console.log('🧠 Agent Learning:');
    const scopeInsights = insights.filter(i => i.type === 'scope_added');
    console.log(`   - Learned about ${scopeInsights.length} OAuth scopes`);
    console.log(`   - Total insights generated: ${insights.length}`);

    // Get suggested next action
    const nextStepInsight = insights.find(i => i.type === 'next_step');
    if (nextStepInsight) {
      console.log(`\n   💡 Agent suggests: ${nextStepInsight.message}`);
    }
  }

  await agent.cleanup();
}

/**
 * Helper: Create progress bar
 */
function createProgressBar(percentage: number, width: number = 30): string {
  const filled = Math.round((percentage / 100) * width);
  const empty = width - filled;
  return `[${'█'.repeat(filled)}${'░'.repeat(empty)}]`;
}

/**
 * Helper: Format conversational messages
 */
function formatConversationalMessage(type: string, message: string): string {
  const timestamp = new Date().toLocaleTimeString();
  const icon = type === 'status' ? '🤖' : '💡';
  return `${timestamp} ${icon} [AGENT] ${message}`;
}

/**
 * Run examples
 */
async function main() {
  const example = process.argv[2] || '1';

  switch (example) {
    case '1':
      await simpleSlackOAuthSetup();
      break;
    case '2':
      await conversationalSlackSetup();
      break;
    case '3':
      await multiTaskWorkflow();
      break;
    default:
      console.log('Usage: ts-node slack_oauth_example.ts [1|2|3]');
      console.log('  1 - Simple task execution with console feedback');
      console.log('  2 - Conversational task with natural language');
      console.log('  3 - Multi-task workflow with learning');
  }
}

// Run if executed directly
if (require.main === module) {
  main().catch(console.error);
}

export {
  simpleSlackOAuthSetup,
  conversationalSlackSetup,
  multiTaskWorkflow
};
