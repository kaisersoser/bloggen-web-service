"use client";

import React from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import type { StreamingContentState } from "@/types/blog";
import { Brain, FileText, Loader2, Search, Target } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";

interface DraftPreviewDialogProps {
  isOpen: boolean;
  onOpenChange: Dispatch<SetStateAction<boolean>>;
  streamingContent: StreamingContentState;
  isGenerating: boolean;
}

export function DraftPreviewDialog({
  isOpen,
  onOpenChange,
  streamingContent,
}: DraftPreviewDialogProps) {
  const hasContent =
    streamingContent.content_preview ||
    streamingContent.research_findings.length > 0 ||
    streamingContent.content_paragraphs.length > 0 ||
    streamingContent.fact_corrections.length > 0;

  return (
    <div className="flex justify-end mb-4">
      <Dialog open={isOpen} onOpenChange={onOpenChange}>
        <DialogTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="flex items-center gap-2 hover:bg-blue-50 hover:border-blue-300"
          >
            <Search className="h-4 w-4" />
            Draft Preview
            {streamingContent.content_paragraphs.length > 0 && (
              <Badge variant="secondary" className="ml-1 text-xs bg-green-100 text-green-800">
                {streamingContent.content_paragraphs.length}
              </Badge>
            )}
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Search className="h-5 w-5" />
              Draft Blog Content Preview
              <Badge variant="outline" className="text-xs">
                {streamingContent.current_phase || 'Generating...'}
              </Badge>
            </DialogTitle>
          </DialogHeader>
          <div className="overflow-y-auto max-h-[60vh] space-y-6">
            {streamingContent.research_findings.length > 0 && (
              <section>
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Brain className="h-5 w-5 text-blue-600" />
                  Research Findings ({streamingContent.research_findings.length})
                </h3>
                <div className="space-y-2">
                  {streamingContent.research_findings.map((finding, index) => (
                    <div key={index} className="p-3 bg-blue-50 rounded-lg border-l-4 border-blue-400">
                      <p className="text-sm text-gray-700">{finding}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {streamingContent.content_paragraphs.length > 0 && (
              <section>
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <FileText className="h-5 w-5 text-green-600" />
                  Draft Content ({streamingContent.content_paragraphs.length} paragraphs)
                </h3>
                <div className="space-y-4">
                  {streamingContent.content_paragraphs.map((paragraph, index) => (
                    <div key={index} className="p-4 bg-green-50 rounded-lg">
                      <p className="text-gray-800 leading-relaxed">{paragraph}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {streamingContent.content_preview && (
              <section>
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <FileText className="h-5 w-5 text-purple-600" />
                  Live Preview
                </h3>
                <div className="p-4 bg-purple-50 rounded-lg">
                  <div className="prose prose-sm max-w-none">
                    <pre className="whitespace-pre-wrap text-gray-800 font-sans">
                      {streamingContent.content_preview}
                    </pre>
                  </div>
                </div>
              </section>
            )}

            {streamingContent.fact_corrections.length > 0 && (
              <section>
                <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                  <Target className="h-5 w-5 text-orange-600" />
                  Fact Corrections ({streamingContent.fact_corrections.length})
                </h3>
                <div className="space-y-2">
                  {streamingContent.fact_corrections.map((correction, index) => (
                    <div key={index} className="p-3 bg-orange-50 rounded-lg border-l-4 border-orange-400">
                      <p className="text-sm text-gray-700">{correction}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {!hasContent && (
              <div className="text-center py-8">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
                <p className="text-gray-500">Waiting for content generation to begin...</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
