import { useState, useCallback } from 'react';
import { StreamingContentState, ContentStreamMessage, ProgressStreamMessage } from '@/types/blog';

export function useStreamingContent() {
  const [streamingContent, setStreamingContent] = useState<StreamingContentState>({
    research_findings: [],
    content_paragraphs: [],
    fact_corrections: [],
    final_content: undefined,
    current_phase: '',
    content_preview: '',
    last_sequence: 0,
  });

  const resetStreamingContent = useCallback(() => {
    setStreamingContent({
      research_findings: [],
      content_paragraphs: [],
      fact_corrections: [],
      final_content: undefined,
      current_phase: '',
      content_preview: '',
      last_sequence: 0,
    });
  }, []);

  const handleContentStreamMessage = useCallback((message: ContentStreamMessage) => {
    setStreamingContent(prev => {
      const newState = { ...prev };
      
      // Update sequence tracking
      newState.last_sequence = Math.max(prev.last_sequence, message.sequence_number);
      newState.current_phase = message.phase;

      // Add content based on type
      switch (message.content_type) {
        case 'research_finding':
          if (!newState.research_findings.includes(message.content)) {
            newState.research_findings = [...newState.research_findings, message.content];
          }
          break;
          
        case 'paragraph':
          if (!newState.content_paragraphs.includes(message.content)) {
            newState.content_paragraphs = [...newState.content_paragraphs, message.content];
          }
          break;
          
        case 'correction':
          if (!newState.fact_corrections.includes(message.content)) {
            newState.fact_corrections = [...newState.fact_corrections, message.content];
          }
          break;
          
        case 'final_content':
          newState.final_content = message.content;
          break;
          
        default:
          // Generic content update
          newState.content_preview = message.content;
      }

      return newState;
    });
  }, []);

  const handleProgressStreamMessage = useCallback((message: ProgressStreamMessage) => {
    setStreamingContent(prev => ({
      ...prev,
      current_phase: message.phase,
      content_preview: message.content_preview || prev.content_preview,
      research_findings: message.research_findings || prev.research_findings,
    }));
  }, []);

  const buildContentPreview = useCallback(() => {
    const parts: string[] = [];
    
    if (streamingContent.research_findings.length > 0) {
      parts.push('## Research Insights');
      streamingContent.research_findings.slice(-3).forEach(finding => {
        parts.push(`• ${finding}`);
      });
      parts.push('');
    }
    
    if (streamingContent.content_paragraphs.length > 0) {
      parts.push('## Blog Content');
      streamingContent.content_paragraphs.forEach(paragraph => {
        parts.push(paragraph);
        parts.push('');
      });
    }
    
    if (streamingContent.fact_corrections.length > 0) {
      parts.push('## Corrections Applied');
      streamingContent.fact_corrections.slice(-2).forEach(correction => {
        parts.push(`✓ ${correction}`);
      });
    }
    
    return parts.join('\n');
  }, [streamingContent]);

  const getStreamingStats = useCallback(() => {
    return {
      total_items: streamingContent.research_findings.length + 
                   streamingContent.content_paragraphs.length + 
                   streamingContent.fact_corrections.length,
      research_count: streamingContent.research_findings.length,
      content_count: streamingContent.content_paragraphs.length,
      corrections_count: streamingContent.fact_corrections.length,
      current_phase: streamingContent.current_phase,
      sequence: streamingContent.last_sequence,
      has_final_content: !!streamingContent.final_content,
    };
  }, [streamingContent]);

  return {
    streamingContent,
    resetStreamingContent,
    handleContentStreamMessage,
    handleProgressStreamMessage,
    buildContentPreview,
    getStreamingStats,
  };
}
