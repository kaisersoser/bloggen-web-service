/**
 * PhaseNode Component
 * 
 * Displays high-level workflow phases (Research, Content Generation, Fact Checking, Finalization)
 * with progress bar and status-based styling.
 * 
 * Features:
 * - Progress bar showing phase completion percentage
 * - Status-based border colors (pending/in_progress/completed/failed)
 * - Active phase highlighting with glow effect
 * - Framer Motion animations for smooth transitions
 */

'use client';

import React from 'react';
import { Handle, Position } from 'reactflow';
import { motion } from 'framer-motion';
import { CheckCircle2, Circle, XCircle, Loader2 } from 'lucide-react';
import type { WorkflowNode } from '@/types/workflow-graph';
import { cn } from '@/lib/utils';

interface PhaseNodeProps {
  data: WorkflowNode;
  selected?: boolean;
}

/**
 * Get status icon based on node status
 */
const StatusIcon = ({ status }: { status: WorkflowNode['status'] }) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="h-5 w-5 text-green-600" />;
    case 'failed':
      return <XCircle className="h-5 w-5 text-red-600" />;
    case 'in_progress':
      return <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />;
    case 'pending':
    default:
      return <Circle className="h-5 w-5 text-gray-400" />;
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
        'border-green-500 bg-green-50',
        selected && 'ring-2 ring-green-300 ring-offset-2'
      );
    case 'failed':
      return cn(
        baseClasses,
        'border-red-500 bg-red-50',
        selected && 'ring-2 ring-red-300 ring-offset-2'
      );
    case 'in_progress':
      return cn(
        baseClasses,
        'border-blue-500 bg-blue-50 shadow-lg shadow-blue-500/30',
        selected && 'ring-2 ring-blue-300 ring-offset-2'
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

export function PhaseNode({ data, selected = false }: PhaseNodeProps) {
  const { label, status, progress = 0, metadata } = data;

  return (
    <>
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white"
      />

      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.8, opacity: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className={cn(
          'min-w-[220px] rounded-xl p-4 shadow-md',
          getStatusStyles(status, selected)
        )}
      >
        {/* Header with icon and label */}
        <div className="flex items-center gap-3 mb-3">
          <StatusIcon status={status} />
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 text-sm">
              {label}
            </h3>
            {metadata.stepNumber && metadata.totalSteps && (
              <p className="text-xs text-gray-500">
                Step {metadata.stepNumber}/{metadata.totalSteps}
              </p>
            )}
          </div>
        </div>

        {/* Progress bar */}
        {status !== 'pending' && (
          <div className="space-y-1">
            <div className="flex justify-between items-center text-xs text-gray-600">
              <span>Progress</span>
              <span className="font-medium">{Math.round(progress)}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
                className={cn(
                  'h-full rounded-full',
                  status === 'completed' && 'bg-green-500',
                  status === 'failed' && 'bg-red-500',
                  status === 'in_progress' && 'bg-blue-500'
                )}
              />
            </div>
          </div>
        )}

        {/* Pulsing animation for active phase */}
        {status === 'in_progress' && (
          <motion.div
            className="absolute inset-0 rounded-xl border-2 border-blue-400"
            animate={{
              opacity: [0.5, 0, 0.5],
              scale: [1, 1.05, 1],
            }}
            transition={{
              duration: 2,
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
        className="!w-3 !h-3 !bg-blue-500 !border-2 !border-white"
      />
    </>
  );
}
