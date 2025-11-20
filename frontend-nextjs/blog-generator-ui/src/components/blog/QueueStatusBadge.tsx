"use client";

import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Clock, Loader2, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

interface QueueStatusBadgeProps {
  status: 'QUEUED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  queuePosition?: number | null;
  retryCount?: number;
  progress?: number;
  compact?: boolean;
}

export const QueueStatusBadge: React.FC<QueueStatusBadgeProps> = ({
  status,
  queuePosition,
  retryCount = 0,
  progress = 0,
  compact = false,
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'QUEUED':
        return {
          icon: Clock,
          label: queuePosition ? `Queue #${queuePosition}` : 'Queued',
          variant: 'secondary' as const,
          className: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
        };
      case 'IN_PROGRESS':
        return {
          icon: Loader2,
          label: compact ? `${progress}%` : `Generating ${progress}%`,
          variant: 'default' as const,
          className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
          animate: true,
        };
      case 'COMPLETED':
        return {
          icon: CheckCircle2,
          label: 'Completed',
          variant: 'default' as const,
          className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
        };
      case 'FAILED':
        return {
          icon: XCircle,
          label: retryCount > 0 ? `Failed (${retryCount} retries)` : 'Failed',
          variant: 'destructive' as const,
          className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
        };
      default:
        return {
          icon: AlertCircle,
          label: 'Unknown',
          variant: 'outline' as const,
          className: '',
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={`flex items-center gap-1.5 ${config.className}`}>
      <Icon 
        className={`h-3.5 w-3.5 ${config.animate ? 'animate-spin' : ''}`}
      />
      <span className="text-xs font-medium">{config.label}</span>
    </Badge>
  );
};

export default QueueStatusBadge;
