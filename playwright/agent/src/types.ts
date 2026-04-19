/**
 * Type definitions for Browser Automation Agent
 */

/**
 * Agent Task - represents a task to be executed
 */
export interface AgentTask {
  id: string;
  description: string;
  params?: Record<string, any>;
  browserOptions?: BrowserOptions;
  priority?: 'low' | 'medium' | 'high' | 'critical';
  createdAt: string;
  timeout?: number;
}

/**
 * Browser configuration options
 */
export interface BrowserOptions {
  headless?: boolean;
  slowMo?: number;
  contextOptions?: Record<string, any>;
  screenshots?: boolean;
  videoRecording?: boolean;
}

/**
 * Agent Status - real-time status updates during execution
 */
export interface AgentStatus {
  stage: 'starting' | 'initialization' | 'navigation' | 'scope_addition' | 'completed' | 'error';
  message: string;
  taskId?: string;
  timestamp: string;
  progress?: {
    current: number;
    total: number;
    percentage: number;
  };
  error?: any;
}

/**
 * Agent Insight - intelligent insights during execution
 */
export interface AgentInsight {
  type: 'task_analysis' | 'initialization' | 'page_analysis' | 'scope_analysis' |
        'scope_added' | 'completion' | 'next_step' | 'warning' | 'error' | 'learning' |
        'state_loaded' | 'state_info' | 'state_saved' | 'state_cleared' | 'cleanup';
  message: string;
  timestamp: string;
  confidence?: number;
  data?: Record<string, any>;
  actionable?: boolean;
  suggestedAction?: string;
  category?: 'explanation' | 'security' | 'suggestion' | 'performance';
  priority?: 'low' | 'medium' | 'high';
}

/**
 * Task Result - outcome of task execution
 */
export interface TaskResult {
  success: boolean;
  taskId: string;
  executionTime: number;
  data?: Record<string, any>;
  error?: string;
  screenshots?: string[];
  logs?: string[];
}

/**
 * Execution Context - maintains state across tasks
 */
export interface ExecutionContext {
  startTime: number | null;
  taskHistory: TaskHistoryEntry[];
  insights: AgentInsight[];
  metrics: ExecutionMetrics;
}

/**
 * Task History Entry
 */
export interface TaskHistoryEntry {
  taskId: string;
  description: string;
  startTime: number;
  endTime: number;
  result: TaskResult;
}

/**
 * Execution Metrics
 */
export interface ExecutionMetrics {
  tasksCompleted: number;
  tasksFailed: number;
  averageExecutionTime: number;
  successRate: number;
}

/**
 * Natural Language Task Plan
 */
export interface TaskPlan {
  intent: string;
  steps: TaskStep[];
  estimatedTime: number;
  requiredTools: string[];
  risksIdentified: Risk[];
  interactionPoints: Checkpoint[];
}

/**
 * Task Step
 */
export interface TaskStep {
  action: string;
  target?: string;
  verify?: boolean;
  critical?: boolean;
  scopes?: string[];
}

/**
 * Risk
 */
export interface Risk {
  type: string;
  mitigation: string;
  severity?: 'low' | 'medium' | 'high';
}

/**
 * Checkpoint - interaction point with user
 */
export interface Checkpoint {
  when: 'before_start' | 'after_completion' | 'on_error' | 'custom';
  ask: string;
  question?: string;
}

/**
 * Agent Configuration
 */
export interface AgentConfiguration {
  agentId: string;
  name: string;
  capabilities: string[];
  defaultBrowserOptions?: BrowserOptions;
  feedbackEnabled?: boolean;
  insightsEnabled?: boolean;
  learningEnabled?: boolean;
}
