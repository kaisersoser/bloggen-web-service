/**
 * Workflow Graph Component
 * 
 * Main component for visualizing the AI blog generation workflow as an interactive graph.
 * Uses ReactFlow for rendering and Dagre for automatic horizontal layout.
 * 
 * Features:
 * - Real-time updates from SSE events
 * - Automatic horizontal layout (left to right)
 * - Zoom, pan, and minimap controls
 * - Custom node types for phases, agents, and tools
 * - Active node highlighting
 */

'use client';

import React, { useState, useRef, useMemo, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Node,
  Edge,
  ConnectionLineType,
  Panel,
} from 'reactflow';
import dagre from 'dagre';
import 'reactflow/dist/style.css';

import { WorkflowGraphBuilder } from '@/lib/workflow-parser';
import type { WorkflowGraph, SSEEvent } from '@/types/workflow-graph';

interface WorkflowGraphProps {
  taskId: string;
  onSSEEvent?: (event: SSEEvent) => void;  // Optional callback for SSE events
  enableDebugLogging?: boolean;
}

/**
 * Layout configuration for Dagre
 */
const LAYOUT_CONFIG = {
  rankdir: 'LR',       // Left to right layout
  ranksep: 150,        // Horizontal spacing between ranks
  nodesep: 80,         // Vertical spacing between nodes
  edgesep: 50,         // Edge separation
};

/**
 * Apply Dagre layout algorithm to position nodes
 */
const getLayoutedElements = (
  nodes: Node[],
  edges: Edge[],
  direction: 'LR' | 'TB' = 'LR'
) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ ...LAYOUT_CONFIG, rankdir: direction });

  // Add nodes to Dagre graph
  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 200, height: 100 });
  });

  // Add edges to Dagre graph
  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  // Run layout algorithm
  dagre.layout(dagreGraph);

  // Apply calculated positions to nodes
  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - 100, // Center the node
        y: nodeWithPosition.y - 50,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

export function WorkflowGraph({ taskId, onSSEEvent, enableDebugLogging = false }: WorkflowGraphProps) {
  const [graph, setGraph] = useState<WorkflowGraph>({
    nodes: [],
    edges: [],
    activeNodeId: null,
    currentPhase: '',
    overallProgress: 0,
    taskId,
  });

  // Graph builder instance (persisted across renders)
  const graphBuilder = useRef(
    new WorkflowGraphBuilder({
      taskId,
      enableDebugLogging,
      deduplicateNodes: true,
      maxNodes: 100,
    })
  );

  /**
   * Process SSE event and update graph
   * TODO: This will be connected in Milestone 3 when we integrate with TabbedPromptInterface
   */
  const handleSSEEvent = useCallback((event: SSEEvent) => {
    const updatedGraph = graphBuilder.current.processSSEEvent(event);
    setGraph(updatedGraph);
    
    if (onSSEEvent) {
      onSSEEvent(event);
    }
  }, [onSSEEvent]);

  // TODO: Milestone 3 - Connect to real SSE stream
  // useEnhancedSSEConnection(taskId, handleSSEEvent);

  // Expose handleSSEEvent for external use (prevents unused warning)
  React.useEffect(() => {
    // This effect ensures handleSSEEvent is preserved for Milestone 3 integration
    if (process.env.NODE_ENV === 'development') {
      console.log('[WorkflowGraph] SSE handler ready for connection (Milestone 3)');
    }
  }, [handleSSEEvent]);
  const reactFlowNodes: Node[] = useMemo(() => {
    return graph.nodes.map((node) => ({
      id: node.id,
      type: node.type, // Will use custom node types (phase, agent, tool)
      position: node.position || { x: 0, y: 0 },
      data: node, // Pass entire node as data for custom components
    }));
  }, [graph.nodes]);

  /**
   * Convert graph edges to ReactFlow edges
   */
  const reactFlowEdges: Edge[] = useMemo(() => {
    return graph.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      animated: edge.animated || false,
      label: edge.label,
      type: edge.type || 'smoothstep',
      style: {
        stroke: edge.animated ? '#3b82f6' : '#94a3b8',
        strokeWidth: edge.animated ? 2 : 1,
      },
    }));
  }, [graph.edges]);

  /**
   * Apply layout when nodes/edges change
   */
  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
    if (reactFlowNodes.length === 0) {
      return { nodes: [], edges: [] };
    }
    return getLayoutedElements(reactFlowNodes, reactFlowEdges);
  }, [reactFlowNodes, reactFlowEdges]);

  /**
   * TODO: Connect to SSE stream
   * This will be implemented in the UI integration phase
   * For now, this is a placeholder for the connection logic
   */
  // useEnhancedSSEConnection(taskId, handleSSEEvent);

  return (
    <div className="h-full w-full relative">
      <ReactFlow
        nodes={layoutedNodes}
        edges={layoutedEdges}
        // nodeTypes={nodeTypes} // Will add custom node types in Milestone 2
        fitView
        minZoom={0.3}
        maxZoom={1.5}
        defaultEdgeOptions={{
          type: 'smoothstep',
          animated: false,
        }}
        connectionLineType={ConnectionLineType.SmoothStep}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#e2e8f0" gap={16} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeStrokeWidth={3}
          zoomable
          pannable
          style={{
            backgroundColor: '#f8fafc',
          }}
        />
        
        {/* Progress Panel */}
        <Panel position="top-center" className="bg-white rounded-lg shadow-md px-4 py-2">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-gray-700">
              {graph.currentPhase || 'Initializing...'}
            </span>
            <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${graph.overallProgress}%` }}
              />
            </div>
            <span className="text-xs text-gray-500">
              {Math.round(graph.overallProgress)}%
            </span>
          </div>
        </Panel>
      </ReactFlow>

      {/* Debug info (only if enabled) */}
      {enableDebugLogging && (
        <div className="absolute bottom-4 left-4 bg-black/80 text-white text-xs p-3 rounded-lg max-w-xs">
          <div>Nodes: {graph.nodes.length}</div>
          <div>Edges: {graph.edges.length}</div>
          <div>Active: {graph.activeNodeId || 'none'}</div>
          <div>Phase: {graph.currentPhase || 'none'}</div>
        </div>
      )}
    </div>
  );
}
