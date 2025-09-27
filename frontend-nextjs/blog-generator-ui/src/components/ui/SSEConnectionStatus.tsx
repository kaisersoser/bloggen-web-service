import React from 'react';
import { AlertCircle, CheckCircle, Loader2, RefreshCw, Wifi, WifiOff } from 'lucide-react';
import { Button } from '@/components/ui/button';

type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'offline_wait' | 'closed' | 'error';

interface SSEConnectionStatusProps {
  status?: ConnectionStatus | null;
  message?: string | null;
  updatedAt?: string | null;
  onRetry?: () => void;
  className?: string;
}

export function SSEConnectionStatus({
  status = 'idle',
  message,
  updatedAt,
  onRetry,
  className = ''
}: SSEConnectionStatusProps) {
  if (!status || status === 'idle') {
    return null;
  }

  const formattedTimestamp = updatedAt
    ? new Date(updatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null;

  const statusConfig: Record<Exclude<ConnectionStatus, 'idle'>, {
    icon: React.ReactNode;
    className: string;
    label: string;
  }> = {
    connecting: {
      icon: <Loader2 className="w-4 h-4 text-blue-600 dark:text-blue-300 animate-spin flex-shrink-0" />, 
      className: 'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200',
      label: 'Connecting to live updates…',
    },
    connected: {
      icon: <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-300 flex-shrink-0" />, 
      className: 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800 text-green-800 dark:text-green-200',
      label: 'Live updates connected',
    },
    reconnecting: {
      icon: <RefreshCw className="w-4 h-4 text-amber-600 dark:text-amber-300 animate-spin flex-shrink-0" />, 
      className: 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-100',
      label: 'Reconnecting…',
    },
    offline_wait: {
      icon: <Wifi className="w-4 h-4 text-purple-600 dark:text-purple-300 flex-shrink-0" />, 
      className: 'bg-purple-50 dark:bg-purple-950/20 border-purple-200 dark:border-purple-800 text-purple-800 dark:text-purple-200',
      label: 'Waiting for network…',
    },
    closed: {
      icon: <WifiOff className="w-4 h-4 text-gray-500 dark:text-gray-300 flex-shrink-0" />, 
      className: 'bg-gray-100 dark:bg-gray-900/40 border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200',
      label: 'Live updates ended',
    },
    error: {
      icon: <AlertCircle className="w-4 h-4 text-red-600 dark:text-red-300 flex-shrink-0" />, 
      className: 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800 text-red-800 dark:text-red-200',
      label: 'Connection issue',
    },
  };

  const config = statusConfig[status] ?? statusConfig.error;

  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 border rounded-md text-sm transition-colors ${config.className} ${className}`}
    >
      {config.icon}
      <div className="flex-1">
        <p className="font-medium leading-tight">
          {config.label}
        </p>
        {(message || formattedTimestamp) && (
          <p className="text-xs opacity-80 leading-tight">
            {message || 'Monitoring connection health.'}
            {formattedTimestamp && ` · ${formattedTimestamp}`}
          </p>
        )}
      </div>
      {status === 'error' && onRetry && (
        <Button
          size="sm"
          variant="outline"
          onClick={onRetry}
          className="ml-2"
        >
          Retry
        </Button>
      )}
    </div>
  );
}
