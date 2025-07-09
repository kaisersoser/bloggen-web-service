import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface ErrorInfo {
  error_type: string;
  user_message: string;
  technical_details: string;
  is_recoverable: boolean;
  suggestions: string[];
  timestamp: string;
  severity: string;
}

interface ErrorDisplayProps {
  error: ErrorInfo;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export function ErrorDisplay({ error, onRetry, onDismiss, className = "" }: ErrorDisplayProps) {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-50 border-red-200 text-red-800';
      case 'medium':
        return 'bg-orange-50 border-orange-200 text-orange-800';
      case 'low':
        return 'bg-yellow-50 border-yellow-200 text-yellow-800';
      default:
        return 'bg-red-50 border-red-200 text-red-800';
    }
  };

  const getErrorIcon = (severity: string) => {
    switch (severity) {
      case 'high':
        return '🚨';
      case 'medium':
        return '⚠️';
      case 'low':
        return '💡';
      default:
        return '❌';
    }
  };

  return (
    <Card className={`${getSeverityStyles(error.severity)} border-2 ${className}`}>
      <CardContent className="p-4">
        <div className="flex items-start space-x-3">
          <span className="text-2xl flex-shrink-0 mt-1">
            {getErrorIcon(error.severity)}
          </span>
          
          <div className="flex-1 min-w-0">
            {/* User-friendly error message */}
            <div className="mb-3">
              <h4 className="font-semibold text-sm mb-1">
                Something went wrong
              </h4>
              <p className="text-sm break-words whitespace-pre-wrap leading-relaxed">
                {error.user_message}
              </p>
            </div>

            {/* Action buttons */}
            <div className="flex flex-wrap gap-2 mb-3">
              {error.is_recoverable && onRetry && (
                <Button 
                  onClick={onRetry}
                  size="sm"
                  className="bg-blue-600 hover:bg-blue-700 text-white"
                >
                  🔄 Try Again
                </Button>
              )}
              
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                className="text-gray-600 border-gray-300"
              >
                {showTechnicalDetails ? '📋 Hide Details' : '🔍 Show Details'}
              </Button>
              
              {onDismiss && (
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={onDismiss}
                  className="text-gray-600 border-gray-300"
                >
                  ✖️ Dismiss
                </Button>
              )}
            </div>

            {/* Technical details (collapsible) */}
            {showTechnicalDetails && (
              <div className="mb-3">
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Technical Details:
                </label>
                <div className="bg-gray-100 p-3 rounded text-xs font-mono max-h-32 overflow-y-auto break-words whitespace-pre-wrap">
                  {error.technical_details}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  Error occurred at: {new Date(error.timestamp).toLocaleString()}
                </p>
              </div>
            )}

            {/* Suggestions */}
            {error.suggestions && error.suggestions.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 p-3 rounded">
                <h5 className="text-sm font-medium text-blue-800 mb-2">
                  💡 Try these solutions:
                </h5>
                <ul className="text-sm text-blue-700 space-y-1">
                  {error.suggestions.map((suggestion, index) => (
                    <li key={index} className="flex items-start break-words">
                      <span className="text-blue-500 mr-2 flex-shrink-0">•</span>
                      <span className="break-words">{suggestion}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
