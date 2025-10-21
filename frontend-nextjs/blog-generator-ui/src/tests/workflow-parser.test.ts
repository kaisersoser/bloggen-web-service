/**
 * Unit Tests for WorkflowGraphBuilder
 * 
 * Tests the core graph building logic that transforms SSE events into workflow nodes and edges.
 */

import { WorkflowGraphBuilder } from '@/lib/workflow-parser';
import type { SSEEvent } from '@/types/workflow-graph';

describe('WorkflowGraphBuilder', () => {
  let builder: WorkflowGraphBuilder;

  beforeEach(() => {
    builder = new WorkflowGraphBuilder({
      taskId: 'test-task-123',
      enableDebugLogging: false,
    });
  });

  describe('initialization', () => {
    it('should initialize with empty graph', () => {
      const graph = builder.getGraph();
      
      expect(graph.nodes).toEqual([]);
      expect(graph.edges).toEqual([]);
      expect(graph.taskId).toBe('test-task-123');
      expect(graph.activeNodeId).toBeNull();
      expect(graph.currentPhase).toBe('');
      expect(graph.overallProgress).toBe(0);
    });
  });

  describe('status events', () => {
    it('should create phase node from status event', () => {
      const event: SSEEvent = {
        type: 'status',
        data: {
          task_id: 'test-task-123',
          status: 'in_progress',
          message: 'Research',
          step: 'Step 2/5',
          progress: 25,
          timestamp: '2025-01-21T10:00:00Z',
        },
      };

      const graph = builder.processSSEEvent(event);

      expect(graph.nodes).toHaveLength(1);
      expect(graph.nodes[0]).toMatchObject({
        type: 'phase',
        label: 'Research',
        status: 'in_progress',
        progress: 25,
      });
      expect(graph.currentPhase).toBe('Research');
      expect(graph.overallProgress).toBe(25);
    });

    it('should update existing phase node', () => {
      const event1: SSEEvent = {
        type: 'status',
        data: {
          task_id: 'test-task-123',
          status: 'in_progress',
          message: 'Research',
          step: 'Step 2/5',
          progress: 25,
          timestamp: '2025-01-21T10:00:00Z',
        },
      };

      const event2: SSEEvent = {
        type: 'status',
        data: {
          task_id: 'test-task-123',
          status: 'in_progress',
          message: 'Research',
          step: 'Step 2/5',
          progress: 30,
          timestamp: '2025-01-21T10:01:00Z',
        },
      };

      builder.processSSEEvent(event1);
      const graph = builder.processSSEEvent(event2);

      expect(graph.nodes).toHaveLength(1);
      expect(graph.nodes[0].progress).toBe(30);
    });

    it('should create edges between sequential phases', () => {
      const event1: SSEEvent = {
        type: 'status',
        data: {
          task_id: 'test-task-123',
          status: 'in_progress',
          message: 'Research',
          step: 'Step 2/5',
          progress: 25,
          timestamp: '2025-01-21T10:00:00Z',
        },
      };

      const event2: SSEEvent = {
        type: 'status',
        data: {
          task_id: 'test-task-123',
          status: 'in_progress',
          message: 'Content Generation',
          step: 'Step 3/5',
          progress: 50,
          timestamp: '2025-01-21T10:05:00Z',
        },
      };

      builder.processSSEEvent(event1);
      const graph = builder.processSSEEvent(event2);

      expect(graph.nodes).toHaveLength(2);
      expect(graph.edges).toHaveLength(1);
      expect(graph.edges[0]).toMatchObject({
        source: 'phase-research',
        target: 'phase-content-generation',
      });
    });
  });

  describe('agent_thinking events', () => {
    it('should create agent node from agent_thinking event', () => {
      const event: SSEEvent = {
        type: 'agent_thinking',
        data: {
          task_id: 'test-task-123',
          status: 'thinking',
          message: 'Analyzing trends',
          agent_name: 'Senior Researcher',
          reasoning: 'Searching for latest AI developments',
          timestamp: '2025-01-21T10:00:00Z',
        },
      };

      const graph = builder.processSSEEvent(event);

      expect(graph.nodes).toHaveLength(1);
      expect(graph.nodes[0]).toMatchObject({
        type: 'agent',
        label: 'Senior Researcher',
        status: 'in_progress',
      });
      expect(graph.nodes[0].metadata.agentName).toBe('Senior Researcher');
      expect(graph.nodes[0].metadata.reasoning).toBe('Searching for latest AI developments');
    });

    it('should link agent to current phase', () => {
      // First create a phase
      const phaseEvent: SSEEvent = {
        type: 'status',
        data: {
          task_id: 'test-task-123',
          status: 'in_progress',
          message: 'Research',
          step: 'Step 2/5',
          progress: 25,
          timestamp: '2025-01-21T10:00:00Z',
        },
      };

      // Then create an agent
      const agentEvent: SSEEvent = {
        type: 'agent_thinking',
        data: {
          task_id: 'test-task-123',
          status: 'thinking',
          message: 'Analyzing trends',
          agent_name: 'Senior Researcher',
          timestamp: '2025-01-21T10:01:00Z',
        },
      };

      builder.processSSEEvent(phaseEvent);
      const graph = builder.processSSEEvent(agentEvent);

      expect(graph.nodes).toHaveLength(2);
      expect(graph.edges).toHaveLength(1);
      expect(graph.edges[0].source).toBe('phase-research');
      expect(graph.edges[0].target).toContain('agent-senior-researcher');
    });
  });

  describe('tool_usage events', () => {
    it('should create tool node from tool_usage event', () => {
      const event: SSEEvent = {
        type: 'tool_usage',
        data: {
          task_id: 'test-task-123',
          status: 'running',
          message: 'Searching web',
          tool_name: 'Serper Search',
          tool_status: 'started',
          timestamp: '2025-01-21T10:00:00Z',
        },
      };

      const graph = builder.processSSEEvent(event);

      expect(graph.nodes).toHaveLength(1);
      expect(graph.nodes[0]).toMatchObject({
        type: 'tool',
        label: 'Serper Search',
        status: 'in_progress',
      });
    });

    it('should update tool status to completed', () => {
      const startEvent: SSEEvent = {
        type: 'tool_usage',
        data: {
          task_id: 'test-task-123',
          status: 'running',
          message: 'Searching web',
          tool_name: 'Serper Search',
          tool_status: 'started',
          timestamp: '2025-01-21T10:00:00Z',
        },
      };

      const finishEvent: SSEEvent = {
        type: 'tool_usage',
        data: {
          task_id: 'test-task-123',
          status: 'completed',
          message: 'Search complete',
          tool_name: 'Serper Search',
          tool_status: 'finished',
          tool_output: 'Found 10 results',
          timestamp: '2025-01-21T10:00:05Z',
        },
      };

      builder.processSSEEvent(startEvent);
      const graph = builder.processSSEEvent(finishEvent);

      expect(graph.nodes).toHaveLength(1);
      expect(graph.nodes[0].status).toBe('completed');
      expect(graph.nodes[0].metadata.toolOutput).toBe('Found 10 results');
    });

    it('should link tool to current agent', () => {
      // Create phase, then agent, then tool
      const phaseEvent: SSEEvent = {
        type: 'status',
        data: {
          task_id: 'test-task-123',
          status: 'in_progress',
          message: 'Research',
          step: 'Step 2/5',
          progress: 25,
          timestamp: '2025-01-21T10:00:00Z',
        },
      };

      const agentEvent: SSEEvent = {
        type: 'agent_thinking',
        data: {
          task_id: 'test-task-123',
          status: 'thinking',
          message: 'Analyzing trends',
          agent_name: 'Senior Researcher',
          timestamp: '2025-01-21T10:01:00Z',
        },
      };

      const toolEvent: SSEEvent = {
        type: 'tool_usage',
        data: {
          task_id: 'test-task-123',
          status: 'running',
          message: 'Searching web',
          tool_name: 'Serper Search',
          tool_status: 'started',
          timestamp: '2025-01-21T10:02:00Z',
        },
      };

      builder.processSSEEvent(phaseEvent);
      builder.processSSEEvent(agentEvent);
      const graph = builder.processSSEEvent(toolEvent);

      expect(graph.nodes).toHaveLength(3);
      expect(graph.edges).toHaveLength(2);
      
      // Should have edge from phase to agent and agent to tool
      const edgeSources = graph.edges.map(e => e.source);
      expect(edgeSources).toContain('phase-research');
      expect(edgeSources.some(s => s.includes('agent-senior-researcher'))).toBe(true);
    });
  });

  describe('error events', () => {
    it('should mark active node as failed on error', () => {
      const phaseEvent: SSEEvent = {
        type: 'status',
        data: {
          task_id: 'test-task-123',
          status: 'in_progress',
          message: 'Research',
          step: 'Step 2/5',
          progress: 25,
          timestamp: '2025-01-21T10:00:00Z',
        },
      };

      const errorEvent: SSEEvent = {
        type: 'error',
        data: {
          task_id: 'test-task-123',
          status: 'error',
          message: 'API rate limit exceeded',
          error: 'Rate limit error',
          timestamp: '2025-01-21T10:01:00Z',
        },
      };

      builder.processSSEEvent(phaseEvent);
      const graph = builder.processSSEEvent(errorEvent);

      expect(graph.nodes[0].status).toBe('failed');
    });
  });

  describe('reset', () => {
    it('should clear all nodes and edges', () => {
      const event: SSEEvent = {
        type: 'status',
        data: {
          task_id: 'test-task-123',
          status: 'in_progress',
          message: 'Research',
          step: 'Step 2/5',
          progress: 25,
          timestamp: '2025-01-21T10:00:00Z',
        },
      };

      builder.processSSEEvent(event);
      expect(builder.getGraph().nodes).toHaveLength(1);

      builder.reset();
      const graph = builder.getGraph();

      expect(graph.nodes).toEqual([]);
      expect(graph.edges).toEqual([]);
      expect(graph.activeNodeId).toBeNull();
    });
  });
});
