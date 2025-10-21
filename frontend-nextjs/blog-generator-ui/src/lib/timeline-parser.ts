/**
 * Timeline Event Parser
 * 
 * Transforms SSE events into timeline items for visualization.
 * Much simpler than the graph builder - just maintains a linear sequence.
 */

import type { SSEEvent } from '@/types/workflow-graph';
import type {
  TimelineState,
  TimelineItem,
  PhaseItem,
  AgentItem,
  ToolItem,
  TimelineItemStatus,
} from '@/types/timeline';

export class TimelineParser {
  private state: TimelineState;
  private enableDebugLogging: boolean;

  constructor(enableDebugLogging = false) {
    this.enableDebugLogging = enableDebugLogging;
    this.state = {
      items: [],
      currentPhase: null,
      overallProgress: 0,
      startTime: new Date().toISOString(),
    };
  }

  /**
   * Process incoming SSE event and update timeline
   */
  processEvent(event: SSEEvent): TimelineState {
    if (this.enableDebugLogging) {
      console.log('📋 [TimelineParser] Processing event:', event.type, event.data);
    }

    switch (event.type) {
      case 'status':
        this.handleStatusEvent(event);
        break;
      case 'agent_thinking':
        this.handleAgentEvent(event);
        break;
      case 'tool_usage':
        this.handleToolEvent(event);
        break;
      case 'error':
        this.handleErrorEvent(event);
        break;
      default:
        if (this.enableDebugLogging) {
          console.log('📋 [TimelineParser] Unhandled event type:', event.type);
        }
    }

    return this.getState();
  }

  /**
   * Handle status/phase events
   */
  private handleStatusEvent(event: SSEEvent): void {
    const { data } = event;
    const phaseName = this.extractPhaseName(data.message || data.status || '');

    if (!phaseName) return;

    // Check if this phase already exists
    const existingPhase = this.state.items.find(
      (item) => item.type === 'phase' && item.title === phaseName
    ) as PhaseItem | undefined;

    if (existingPhase) {
      // Update existing phase
      existingPhase.status = this.mapStatus(data.status);
      existingPhase.progress = data.progress || existingPhase.progress;
      existingPhase.timestamp = data.timestamp || existingPhase.timestamp;
    } else {
      // Create new phase
      const newPhase: PhaseItem = {
        id: `phase-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        type: 'phase',
        title: phaseName,
        status: this.mapStatus(data.status),
        timestamp: data.timestamp || new Date().toISOString(),
        progress: data.progress || 0,
        expanded: false,
      };
      this.state.items.push(newPhase);
      this.state.currentPhase = newPhase.id;
    }

    this.state.overallProgress = data.progress || this.state.overallProgress;
  }

  /**
   * Handle agent thinking events
   */
  private handleAgentEvent(event: SSEEvent): void {
    const { data } = event;
    
    if (!data.agent_name) return;

    // Find or create agent item
    const agentId = this.generateAgentId(data.agent_name);
    let agent = this.state.items.find((item) => item.id === agentId) as AgentItem | undefined;

    if (agent) {
      // Update existing agent
      agent.status = 'in_progress';
      agent.reasoning = data.reasoning || agent.reasoning;
      agent.timestamp = data.timestamp || agent.timestamp;
    } else {
      // Create new agent
      agent = {
        id: agentId,
        type: 'agent',
        title: data.agent_name,
        role: data.agent_name,
        status: 'in_progress',
        timestamp: data.timestamp || new Date().toISOString(),
        reasoning: data.reasoning,
        phaseId: this.state.currentPhase || undefined,
        expanded: false,
      };
      this.state.items.push(agent);
    }
  }

  /**
   * Handle tool usage events
   */
  private handleToolEvent(event: SSEEvent): void {
    const { data } = event;
    
    if (!data.tool_name) return;

    const toolId = `tool-${data.tool_name}-${Date.now()}`;
    
    const tool: ToolItem = {
      id: toolId,
      type: 'tool',
      title: data.tool_name,
      toolName: data.tool_name,
      status: this.mapToolStatus(data.tool_status),
      timestamp: data.timestamp || new Date().toISOString(),
      output: data.tool_output,
      error: data.tool_error,
      expanded: false,
    };

    this.state.items.push(tool);
  }

  /**
   * Handle error events
   */
  private handleErrorEvent(event: SSEEvent): void {
    const { data } = event;
    
    // Mark current phase/agent as error
    if (this.state.currentPhase) {
      const currentPhase = this.state.items.find(
        (item) => item.id === this.state.currentPhase
      );
      if (currentPhase) {
        currentPhase.status = 'error';
      }
    }

    // Could also create an error item in timeline
    console.error('⚠️ [TimelineParser] Error event:', data.error);
  }

  /**
   * Extract phase name from status message
   */
  private extractPhaseName(message: string): string | null {
    const lowerMessage = message.toLowerCase();

    if (lowerMessage.includes('research')) return 'Research phase';
    if (lowerMessage.includes('content') || lowerMessage.includes('generation')) return 'Content Generation phase';
    if (lowerMessage.includes('fact') || lowerMessage.includes('check')) return 'Fact Checking phase';
    if (lowerMessage.includes('final') || lowerMessage.includes('polish')) return 'Finalization phase';
    if (lowerMessage.includes('initializ')) return 'Initialization';
    if (lowerMessage.includes('deduplic')) return 'Reference deduplication';

    return null;
  }

  /**
   * Generate consistent agent ID
   */
  private generateAgentId(agentName: string): string {
    return `agent-${agentName.toLowerCase().replace(/\s+/g, '-')}`;
  }

  /**
   * Map status strings to timeline status
   */
  private mapStatus(status?: string): TimelineItemStatus {
    if (!status) return 'pending';
    
    const lowerStatus = status.toLowerCase();
    
    if (lowerStatus.includes('progress') || lowerStatus.includes('running')) return 'in_progress';
    if (lowerStatus.includes('complete') || lowerStatus.includes('done')) return 'completed';
    if (lowerStatus.includes('error') || lowerStatus.includes('fail')) return 'error';
    
    return 'pending';
  }

  /**
   * Map tool status to timeline status
   */
  private mapToolStatus(toolStatus?: string): TimelineItemStatus {
    if (!toolStatus) return 'completed';
    
    const lowerStatus = toolStatus.toLowerCase();
    
    if (lowerStatus.includes('error') || lowerStatus.includes('fail')) return 'error';
    if (lowerStatus.includes('success') || lowerStatus.includes('complete')) return 'completed';
    
    return 'completed';
  }

  /**
   * Get current timeline state
   */
  getState(): TimelineState {
    return { ...this.state, items: [...this.state.items] };
  }

  /**
   * Reset timeline state
   */
  reset(): void {
    this.state = {
      items: [],
      currentPhase: null,
      overallProgress: 0,
      startTime: new Date().toISOString(),
    };
  }

  /**
   * Mark timeline as completed
   */
  complete(): void {
    this.state.endTime = new Date().toISOString();
    this.state.overallProgress = 100;
    
    // Mark all in-progress items as completed
    this.state.items.forEach((item) => {
      if (item.status === 'in_progress') {
        item.status = 'completed';
      }
    });
  }
}
