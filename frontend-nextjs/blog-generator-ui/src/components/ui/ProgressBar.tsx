import React from 'react';

interface ProgressBarProps { value: number; className?: string; showLabel?: boolean; }
export const ProgressBar: React.FC<ProgressBarProps> = ({ value, className = '', showLabel = true }) => {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <div className={`w-full bg-gray-200 dark:bg-gray-700 rounded h-3 overflow-hidden ${className}`}> 
      <div 
        className="h-full bg-blue-600 dark:bg-blue-400 transition-all duration-300" 
        style={{ width: `${clamped}%` }}
        aria-valuenow={clamped}
        aria-valuemin={0}
        aria-valuemax={100}
        role="progressbar"
      />
      {showLabel && (
        <span className="sr-only">{clamped}%</span>
      )}
    </div>
  );
};
