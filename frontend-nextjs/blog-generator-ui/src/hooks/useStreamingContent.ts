import { useState, useCallback } from 'react';
import { StreamingContentState } from '@/types/blog';

export function useStreamingContent() {
  const [streamingContent, setStreamingContent] = useState<StreamingContentState>({
    research_findings: [],
    content_paragraphs: [],
    fact_corrections: [],
    final_content: undefined,
    current_phase: '',
    content_preview: '',
    last_sequence: 0
  });

  const handleContentStreamMessage = useCallback((data: any) => {
    if (data.type === 'content_stream') {
      setStreamingContent(prev => {
        const updated = { ...prev };
        
        if (data.content_type === 'research_finding') {
          updated.research_findings = [...prev.research_findings, data.content];
        } else if (data.content_type === 'paragraph') {
          updated.content_paragraphs = [...prev.content_paragraphs, data.content];
        } else if (data.content_type === 'correction') {
          updated.fact_corrections = [...prev.fact_corrections, data.content];
        } else if (data.content_type === 'final_content') {
          updated.final_content = data.content;
        }
        
        updated.current_phase = data.phase || prev.current_phase;
        updated.content_preview = data.content || prev.content_preview;
        updated.last_sequence = data.sequence_number || prev.last_sequence;
        
        return updated;
      });
    }
  }, []);

  const handleProgressStreamMessage = useCallback((data: any) => {
    if (data.type === 'progress_stream') {
      setStreamingContent(prev => ({
        ...prev,
        current_phase: data.phase || prev.current_phase,
        content_preview: data.content_preview || prev.content_preview,
        research_findings: data.research_findings || prev.research_findings
      }));
    }
  }, []);

  const resetStreamingContent = useCallback(() => {
    setStreamingContent({
      research_findings: [],
      content_paragraphs: [],
      fact_corrections: [],
      final_content: undefined,
      current_phase: '',
      content_preview: '',
      last_sequence: 0
    });
  }, []);

  const getStreamingStats = useCallback(() => {
    return {
      contentLength: streamingContent.content_preview.length,
      researchCount: streamingContent.research_findings.length,
      paragraphCount: streamingContent.content_paragraphs.length,
      phase: streamingContent.current_phase,
      isActive: streamingContent.current_phase !== ''
    };
  }, [streamingContent]);

  return {
    streamingContent,
    handleContentStreamMessage,
    handleProgressStreamMessage,
    resetStreamingContent,
    getStreamingStats
  };
}
