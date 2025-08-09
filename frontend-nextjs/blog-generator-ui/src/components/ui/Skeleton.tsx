import React from 'react';
export const Skeleton: React.FC<{ className?: string }> = ({ className = '' }) => (<div className={`animate-pulse rounded-md bg-gray-200 dark:bg-gray-700 ${className}`} />);
