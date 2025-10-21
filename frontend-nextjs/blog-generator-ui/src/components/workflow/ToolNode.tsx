/**
 * ToolNode Component
 * 
 * Displays tool execution (SearchAPITool, UnsplashImageTool, ScraperTool, etc.)
 * with status badges and compact design.
 * 
 * Features:
 * - Tool-specific icons (Search, Image, Globe)
 * - Status badges (running, success, failed)
 * - Compact design for leaf nodes
 * - Subtle animations for active tools
 */

'use client';

import React from 'react';
import { Handle, Position } from 'reactflow';
import { motion } from 'framer-motion';
import { 
  Search, 
  Image, 
  Globe, 
  Wrench, 
  CheckCircle2, 
  XCircle, 
  Loader2 
} from 'lucide-react';
import type { WorkflowNode } from '@/types/workflow-graph';
import { cn } from '@/lib/utils';

interface ToolNodeProps {
  data: WorkflowNode;
  selected?: boolean;
}

/**
 * Get tool-specific icon based on tool name
 */
const ToolIcon = ({ toolName }: { toolName: string }) => {
  const iconClass = "h-3.5 w-3.5 text-blue-600";
  
  if (toolName.toLowerCase().includes('search') || toolName.toLowerCase().includes('serper')) {
    return <Search className={iconClass} />;
  }
  if (toolName.toLowerCase().includes('image') || toolName.toLowerCase().includes('unsplash')) {
    return <Image className={iconClass} aria-label="Image tool" />;
  }
  if (toolName.toLowerCase().includes('scraper') || toolName.toLowerCase().includes('web')) {
    return <Globe className={iconClass} />;
  }
  
  return <Wrench className={iconClass} />;
};

/**
 * Get status badge component
 */
const StatusBadge = ({ status }: { status: WorkflowNode['status'] }) => {
  switch (status) {
    case 'completed':
      return (
        <div className="flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-green-100 text-green-700 border border-green-300">
          <CheckCircle2 className="h-2.5 w-2.5" />
          <span>Success</span>
        </div>
      );
    case 'failed':
      return (
        <div className="flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-red-100 text-red-700 border border-red-300">
          <XCircle className="h-2.5 w-2.5" />
          <span>Failed</span>
        </div>
      );
    case 'in_progress':
      return (
        <div className="flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-blue-100 text-blue-700 border border-blue-300">
          <Loader2 className="h-2.5 w-2.5 animate-spin" />
          <span>Running</span>
        </div>
      );
    case 'pending':
    default:
      return (
        <div className="px-1.5 py-0.5 rounded text-xs bg-gray-100 text-gray-600 border border-gray-300">
          Pending
        </div>
      );
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
        'border-blue-400 bg-blue-50 shadow-sm shadow-blue-500/20',
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

export function ToolNode({ data, selected = false }: ToolNodeProps) {
  const { label, status, metadata } = data;
  const toolName = metadata.toolName || label;

  return (
    <>
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2 !h-2 !bg-blue-500 !border-2 !border-white"
      />

      <motion.div
        initial={{ scale: 0.8, opacity: 0, y: 10 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.8, opacity: 0, y: 10 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className={cn(
          'min-w-[160px] max-w-[220px] rounded-md shadow-sm',
          getStatusStyles(status, selected)
        )}
      >
        <div className="p-2.5">
          {/* Header row */}
          <div className="flex items-center gap-2 mb-1.5">
            <ToolIcon toolName={toolName} />
            <span className="text-xs font-medium text-gray-900 truncate flex-1">
              {label}
            </span>
          </div>

          {/* Status badge */}
          <div className="flex justify-end">
            <StatusBadge status={status} />
          </div>

          {/* Tool input (if available) */}
          {metadata.toolInput && (
            <p className="text-xs text-gray-500 mt-1.5 truncate" title={metadata.toolInput}>
              {metadata.toolInput}
            </p>
          )}
        </div>

        {/* Active progress indicator */}
        {status === 'in_progress' && (
          <div className="px-2.5 pb-2.5">
            <div className="h-0.5 w-full rounded-full bg-blue-200 overflow-hidden">
              <motion.div
                className="h-full bg-blue-500"
                animate={{ width: ['0%', '100%'] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
              />
            </div>
          </div>
        )}

        {/* Subtle pulse for active tool */}
        {status === 'in_progress' && (
          <motion.div
            className="absolute inset-0 rounded-md border-2 border-blue-400"
            animate={{
              opacity: [0.2, 0, 0.2],
            }}
            transition={{
              duration: 1,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}
      </motion.div>

      {/* No output handle - tools are leaf nodes */}
    </>
  );
}
