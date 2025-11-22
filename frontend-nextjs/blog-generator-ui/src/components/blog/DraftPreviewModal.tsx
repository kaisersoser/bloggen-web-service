"use client";

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { RefreshCw, FileText, Eye } from 'lucide-react';
import { DraftContent } from '@/types/queue';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface DraftPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  taskId: string;
  draft: DraftContent | null;
  isLoading?: boolean;
  onRefresh?: () => void;
}

export const DraftPreviewModal: React.FC<DraftPreviewModalProps> = ({
  isOpen,
  onClose,
  taskId,
  draft,
  isLoading = false,
  onRefresh,
}) => {
  const [viewMode, setViewMode] = useState<'preview' | 'raw'>('preview');

  const getSectionNames = () => {
    if (!draft || !draft.sections) return [];
    return Object.keys(draft.sections);
  };

  const getCombinedContent = () => {
    if (!draft || !draft.sections) return '';
    
    const sections = draft.sections;
    let combined = '';
    
    // Add title if available
    if (draft.metadata?.title) {
      combined += `# ${draft.metadata.title}\n\n`;
    }
    
    // Add hero image if available
    if (draft.metadata?.heroImageUrl) {
      combined += `![Hero Image](${draft.metadata.heroImageUrl})\n\n`;
    }
    
    // Combine all sections
    Object.entries(sections).forEach(([sectionName, content]) => {
      if (content) {
        combined += `## ${sectionName}\n\n${content}\n\n`;
      }
    });
    
    return combined || 'No content available yet...';
  };

  const sectionNames = getSectionNames();
  const combinedContent = getCombinedContent();

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-5xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <DialogTitle>Draft Preview</DialogTitle>
              <DialogDescription>
                Partial content for task {taskId.slice(0, 8)}...
              </DialogDescription>
            </div>
            <div className="flex items-center gap-2">
              {onRefresh && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onRefresh}
                  disabled={isLoading}
                  className="gap-2"
                >
                  <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              )}
            </div>
          </div>
          
          {/* Progress bar */}
          {draft && (
            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium">Generation Progress</span>
                <span className="text-sm text-muted-foreground">{draft.progress}%</span>
              </div>
              <ProgressBar value={draft.progress} showLabel={false} className="h-2" />
            </div>
          )}
        </DialogHeader>

        <div className="flex-1 min-h-0 mt-4">
          {isLoading && !draft ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Loading draft...</p>
              </div>
            </div>
          ) : !draft || sectionNames.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <FileText className="h-12 w-12 mx-auto mb-3 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">No draft content available yet</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Content will appear here as it's being generated
                </p>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col">
              {/* View mode toggle */}
              <div className="flex items-center gap-2 mb-3">
                <Button
                  variant={viewMode === 'preview' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('preview')}
                  className="gap-2"
                >
                  <Eye className="h-4 w-4" />
                  Preview
                </Button>
                <Button
                  variant={viewMode === 'raw' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('raw')}
                  className="gap-2"
                >
                  <FileText className="h-4 w-4" />
                  Raw Markdown
                </Button>
              </div>

              {/* Content display */}
              <div className="flex-1 overflow-y-auto border rounded-md">
                {viewMode === 'preview' ? (
                  <div className="p-6 prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {combinedContent}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <pre className="p-6 text-sm font-mono whitespace-pre-wrap break-words">
                    {combinedContent}
                  </pre>
                )}
              </div>

              {/* Section breakdown */}
              {sectionNames.length > 1 && (
                <div className="mt-4 pt-4 border-t">
                  <p className="text-sm font-medium mb-2">Sections Available:</p>
                  <div className="flex flex-wrap gap-2">
                    {sectionNames.map((section) => (
                      <div
                        key={section}
                        className="px-3 py-1 bg-secondary text-secondary-foreground rounded-md text-xs font-medium"
                      >
                        {section}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default DraftPreviewModal;
