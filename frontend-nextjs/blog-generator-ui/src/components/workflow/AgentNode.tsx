/**
 * AgentNode Component
 * 
 * Displays AI agent activity (Senior Researcher, Content Creator, Fact Checker, Editor)
 * with expandable reasoning details.
 * 
 * Features:
 * - Brain icon with agent name
 * - Expandable reasoning section (click to toggle)
 * - Status-based border colors
 * - Pulsing animation when active
 * - Smooth expand/collapse animations
 */

'use client';

import React, { useState } from 'react';
import { Handle, Position } from 'reactflow';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, ChevronDown, ChevronUp, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import type { WorkflowNode } from '@/types/workflow-graph';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface AgentNodeProps {
  data: WorkflowNode;
  selected?: boolean;
}

/**
 * Get status icon based on node status
 */
const StatusIcon = ({ status }: { status: WorkflowNode['status'] }) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-3 w-3 text-green-600" />;
    case 'failed':
      return <XCircle className="h-3 w-3 text-red-600" />;
    case 'in_progress':
      return <Loader2 className="h-3 w-3 text-purple-600 animate-spin" />;
    case 'pending':
    default:
      return null;
  }
};

/**
 * Get status-based styling classes
 */
const getStatusStyles = (status: WorkflowNode['status'], selected: boolean) => {
  const baseClasses = 'border-2 transition-all duration-300';
  
  switch (status) {
    case 'completed':
      return cn(
        baseClasses,
        'border-green-400 bg-green-50',
        selected && 'ring-2 ring-green-300 ring-offset-2'
      );
    case 'failed':
      return cn(
        baseClasses,
        'border-red-400 bg-red-50',
        selected && 'ring-2 ring-red-300 ring-offset-2'
      );
    case 'in_progress':
      return cn(
        baseClasses,
        'border-purple-400 bg-purple-50 shadow-md shadow-purple-500/20',
        selected && 'ring-2 ring-purple-300 ring-offset-2'
      );
    case 'pending':
    default:
      return cn(
        baseClasses,
        'border-gray-300 bg-gray-50',
        selected && 'ring-2 ring-gray-300 ring-offset-2'
      );
  }
};

export function AgentNode({ data, selected = false }: AgentNodeProps) {
  const { label, status, metadata } = data;
  const [expanded, setExpanded] = useState(false);
  const hasReasoning = Boolean(metadata.reasoning);

  return (
    <>
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2 !h-2 !bg-purple-500 !border-2 !border-white"
      />

      <motion.div
        initial={{ scale: 0.8, opacity: 0, x: -20 }}
        animate={{ scale: 1, opacity: 1, x: 0 }}
        exit={{ scale: 0.8, opacity: 0, x: -20 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className={cn(
          'min-w-[200px] max-w-[280px] rounded-lg shadow-sm',
          getStatusStyles(status, selected)
        )}
      >
        {/* Header */}
        <div className="p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 flex-1 min-w-0">
              <Brain className="h-4 w-4 text-purple-600 flex-shrink-0" />
              <span className="text-sm font-medium text-gray-900 truncate">
                {label}
              </span>
              <StatusIcon status={status} />
            </div>
            
            {hasReasoning && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setExpanded(!expanded)}
                className="h-6 w-6 p-0 hover:bg-purple-100"
              >
                {expanded ? (
                  <ChevronUp className="h-3 w-3 text-purple-600" />
                ) : (
                  <ChevronDown className="h-3 w-3 text-purple-600" />
                )}
              </Button>
            )}
          </div>

          {/* Agent role (if available) */}
          {metadata.role && (
            <p className="text-xs text-gray-500 mt-1 truncate">
              {metadata.role}
            </p>
          )}
        </div>

        {/* Expandable reasoning section */}
        <AnimatePresence>
          {expanded && hasReasoning && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: 'easeInOut' }}
              className="overflow-hidden border-t border-purple-200"
            >
              <div className="p-3 bg-purple-50/50">
                <p className="text-xs text-gray-700 leading-relaxed">
                  {metadata.reasoning}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Active progress indicator */}
        {status === 'in_progress' && (
          <div className="px-3 pb-3">
            <div className="h-1 w-full rounded-full bg-purple-200 overflow-hidden">
              <motion.div
                className="h-full bg-purple-500"
                animate={{ width: ['0%', '100%'] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              />
            </div>
          </div>
        )}

        {/* Pulsing animation for active agent */}
        {status === 'in_progress' && (
          <motion.div
            className="absolute inset-0 rounded-lg border-2 border-purple-400"
            animate={{
              opacity: [0.3, 0, 0.3],
              scale: [1, 1.02, 1],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}
      </motion.div>

      {/* Output handle (right side) */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-2 !h-2 !bg-purple-500 !border-2 !border-white"
      />
    </>
  );
}
