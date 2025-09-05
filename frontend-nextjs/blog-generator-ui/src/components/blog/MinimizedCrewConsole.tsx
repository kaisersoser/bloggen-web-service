"use client"
import React, { useState } from 'react';
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  ChevronUp, 
  ChevronDown, 
  Terminal, 
  Activity, 
  Users, 
  Zap,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2
} from "lucide-react";
import { ProgressBar } from "@/components/ui/ProgressBar";

interface TaskLog {
  id: string;
  timestamp: string;
  step: string;
  progress: number;
  details: string;
  status: 'running' | 'completed' | 'error';
}

interface MinimizedCrewConsoleProps {
  isVisible?: boolean;
  isExpanded?: boolean;
  onToggleExpanded?: () => void;
  currentJob?: {
    id: string;
    status: string;
    progress: number;
    topic: string;
  };
  taskLogs?: TaskLog[];
  isGenerating?: boolean;
  className?: string;
}

export function MinimizedCrewConsole({
  isVisible = true,
  isExpanded = false,
  onToggleExpanded,
  currentJob,
  taskLogs = [],
  isGenerating = false,
  className = ""
}: MinimizedCrewConsoleProps) {
  const [localExpanded, setLocalExpanded] = useState(isExpanded);

  const handleToggle = () => {
    const newExpanded = !localExpanded;
    setLocalExpanded(newExpanded);
    onToggleExpanded?.();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Loader2 className="w-3 h-3 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="w-3 h-3 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-3 h-3 text-red-500" />;
      default:
        return <Clock className="w-3 h-3 text-gray-400" />;
    }
  };

  const getAgentSteps = () => {
    const steps = [
      { name: 'Research', status: 'completed', agent: 'Senior Researcher' },
      { name: 'Content Generation', status: 'running', agent: 'Content Creator' },
      { name: 'Fact Checking', status: 'pending', agent: 'Fact Checker' },
      { name: 'Finalization', status: 'pending', agent: 'Blog Finalizer' },
    ];

    return steps;
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className={`fixed bottom-4 right-4 z-50 ${className}`}>
      <Card className={`transition-all duration-300 shadow-lg border ${
        localExpanded ? 'w-96 h-80' : 'w-80 h-16'
      }`}>
        {/* Header - Always Visible */}
        <div 
          className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          onClick={handleToggle}
        >
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-blue-100 dark:bg-blue-900 rounded">
              <Terminal className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h3 className="font-medium text-sm text-gray-900 dark:text-white">
                CrewAI Console
              </h3>
              {isGenerating && currentJob && (
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-48">
                  {currentJob.topic}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isGenerating && (
              <div className="flex items-center gap-1">
                <Activity className="w-3 h-3 text-green-500 animate-pulse" />
                <span className="text-xs text-green-600 dark:text-green-400 font-medium">
                  Active
                </span>
              </div>
            )}
            
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
            >
              {localExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronUp className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Expanded Content */}
        {localExpanded && (
          <div className="border-t p-3 space-y-3 overflow-hidden">
            {/* Progress Overview */}
            {isGenerating && currentJob && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-600 dark:text-gray-400">Overall Progress</span>
                  <span className="font-medium">{Math.round(currentJob.progress)}%</span>
                </div>
                <ProgressBar 
                  value={currentJob.progress} 
                  className="h-1.5"
                  showLabel={false}
                />
              </div>
            )}

            {/* Agent Steps */}
            <div className="space-y-2">
              <div className="flex items-center gap-1 text-xs font-medium text-gray-700 dark:text-gray-300">
                <Users className="w-3 h-3" />
                AI Agents
              </div>
              
              <div className="space-y-1.5 max-h-32 overflow-y-auto">
                {getAgentSteps().map((step) => (
                  <div 
                    key={step.name}
                    className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded text-xs"
                  >
                    <div className="flex items-center gap-2">
                      {getStatusIcon(step.status)}
                      <span className="font-medium">{step.name}</span>
                    </div>
                    <span className="text-gray-500 text-xs">{step.agent}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Logs */}
            {taskLogs.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-1 text-xs font-medium text-gray-700 dark:text-gray-300">
                  <Activity className="w-3 h-3" />
                  Recent Activity
                </div>
                
                <div className="space-y-1 max-h-20 overflow-y-auto">
                  {taskLogs.slice(-3).map((log) => (
                    <div key={log.id} className="text-xs text-gray-600 dark:text-gray-400">
                      <span className="font-medium">{log.step}:</span> {log.details}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Footer Actions */}
            <div className="flex items-center justify-between pt-2 border-t">
              <div className="flex items-center gap-1 text-xs text-gray-500">
                <Zap className="w-3 h-3" />
                <span>AI-Powered</span>
              </div>
              
              {isGenerating && (
                <Button
                  variant="outline"
                  size="sm" 
                  className="h-6 px-2 text-xs"
                  onClick={(e) => {
                    e.stopPropagation();
                    // Handle stop generation if needed
                  }}
                >
                  Stop
                </Button>
              )}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
