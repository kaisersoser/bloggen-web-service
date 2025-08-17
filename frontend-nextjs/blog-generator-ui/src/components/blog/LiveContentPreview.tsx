import { Card, CardContent } from '@/components/ui/card';
import { StreamingContentState } from '@/types/blog';
import { Eye, Search, Edit, CheckCircle, Clock } from 'lucide-react';

interface LiveContentPreviewProps {
  streamingContent: StreamingContentState;
  className?: string;
}

export function LiveContentPreview({ streamingContent, className = '' }: LiveContentPreviewProps) {
  const {
    research_findings,
    content_paragraphs,
    fact_corrections,
    final_content,
    current_phase,
    content_preview,
    last_sequence
  } = streamingContent;

  const getPhaseIcon = (phase: string) => {
    switch (phase) {
      case 'research':
        return <Search className="h-4 w-4" />;
      case 'content_generation':
        return <Edit className="h-4 w-4" />;
      case 'fact_checking':
        return <CheckCircle className="h-4 w-4" />;
      case 'finalization':
        return <Eye className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const getPhaseColor = (phase: string) => {
    switch (phase) {
      case 'research':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'content_generation':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'fact_checking':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      case 'finalization':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Phase Indicator */}
      <div className="flex items-center gap-3">
        <div className={`${getPhaseColor(current_phase)} flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium`}>
          {getPhaseIcon(current_phase)}
          <span className="capitalize">{current_phase.replace('_', ' ')}</span>
        </div>
        {last_sequence > 0 && (
          <span className="text-sm text-gray-500 dark:text-gray-400">
            Sequence: {last_sequence}
          </span>
        )}
      </div>

      {/* Research Findings */}
      {research_findings.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Search className="h-4 w-4 text-blue-600" />
              Research Findings ({research_findings.length})
            </h3>
            <div className="space-y-2">
              {research_findings.map((finding, index) => (
                <div
                  key={index}
                  className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-l-4 border-blue-400 text-sm animate-fade-in"
                >
                  {finding}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Content Paragraphs */}
      {content_paragraphs.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Edit className="h-4 w-4 text-green-600" />
              Generated Content ({content_paragraphs.length} paragraphs)
            </h3>
            <div className="space-y-3">
              {content_paragraphs.map((paragraph, index) => (
                <div
                  key={index}
                  className="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg text-sm leading-relaxed animate-fade-in"
                >
                  {paragraph}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Fact Corrections */}
      {fact_corrections.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-yellow-600" />
              Fact Corrections ({fact_corrections.length})
            </h3>
            <div className="space-y-2">
              {fact_corrections.map((correction, index) => (
                <div
                  key={index}
                  className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border-l-4 border-yellow-400 text-sm animate-fade-in"
                >
                  {correction}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Final Content */}
      {final_content && (
        <Card className="border-purple-200 dark:border-purple-800">
          <CardContent className="p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Eye className="h-4 w-4 text-purple-600" />
              Final Content
            </h3>
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <div className="whitespace-pre-wrap text-sm leading-relaxed animate-fade-in">
                {final_content}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Content Preview */}
      {content_preview && !final_content && (
        <Card className="border-dashed border-gray-300 dark:border-gray-600">
          <CardContent className="p-4">
            <h3 className="font-semibold text-sm mb-3 flex items-center gap-2">
              <Clock className="h-4 w-4 text-gray-600" />
              Live Preview
            </h3>
            <div className="text-sm text-gray-600 dark:text-gray-400 italic animate-pulse">
              {content_preview}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {research_findings.length === 0 && 
       content_paragraphs.length === 0 && 
       fact_corrections.length === 0 && 
       !final_content && 
       !content_preview && (
        <Card className="border-dashed border-gray-300 dark:border-gray-600">
          <CardContent className="p-8 text-center">
            <Clock className="h-8 w-8 text-gray-400 mx-auto mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Waiting for content stream...
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}