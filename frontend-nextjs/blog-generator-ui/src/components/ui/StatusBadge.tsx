import React from 'react';

interface StatusBadgeProps { status: string; children?: React.ReactNode; className?: string; }
const STYLE_MAP: Record<string, string> = { completed: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/30', failed: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/30', in_progress: 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30', queued: 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700' };
export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, children, className = '' }) => { const style = STYLE_MAP[status.toLowerCase()] || STYLE_MAP['queued']; return (<span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${style} ${className}`}>{children || status}</span>); };
