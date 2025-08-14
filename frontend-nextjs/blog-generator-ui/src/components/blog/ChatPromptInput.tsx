import { useState, useRef, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { blogService } from '@/lib/services/blog';
import { Send, Settings } from 'lucide-react';

export interface PromptConfig {
  tone: 'creative-funny' | 'basic-info' | 'deep-research';
  length: 'short' | 'normal' | 'long';
}

interface ChatPromptInputProps {
  onGenerate: (topic: string, instructions: string, config: PromptConfig) => Promise<void>;
  stats: {
    remainingGenerations: number;
    monthlyLimit: number;
  } | null;
  isFree: boolean;
  generationError: string | null;
  statsLoading: boolean;
  isGenerating: boolean;
}

const toneOptions = [
  { value: 'creative-funny' as const, label: 'Funny', description: 'Creatively funny and engaging' },
  { value: 'basic-info' as const, label: 'Basic', description: 'Informative and straightforward' },
  { value: 'deep-research' as const, label: 'Research', description: 'Thoroughly researched with detailed cross-checking' }
];

const lengthOptions = [
  { value: 'short' as const, label: 'Short', description: '800-1200 words' },
  { value: 'normal' as const, label: 'Normal', description: '1200-2000 words' },
  { value: 'long' as const, label: 'Long', description: '2000-3500 words' }
];

export function ChatPromptInput({
  onGenerate,
  stats,
  isFree,
  generationError,
  statsLoading,
  isGenerating
}: ChatPromptInputProps) {
  const [userInput, setUserInput] = useState('');
  const [config, setConfig] = useState<PromptConfig>({
    tone: 'basic-info',
    length: 'normal'
  });
  const [showConfig, setShowConfig] = useState(false);
  const [fullInstructions, setFullInstructions] = useState('');
  const [extractedTopic, setExtractedTopic] = useState('');
  const [generatedTitle, setGeneratedTitle] = useState('');
  const [isGeneratingTitle, setIsGeneratingTitle] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const configRef = useRef<HTMLDivElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [userInput]);

  // Handle closing configuration and writing preview back to main prompt
  const handleConfigClose = useCallback(() => {
    if (showConfig && userInput.trim() && fullInstructions) {
      // Write the full instructions back to the main prompt
      setUserInput(fullInstructions);
    }
    setShowConfig(false);
  }, [showConfig, userInput, fullInstructions]);

  // Close config when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (configRef.current && !configRef.current.contains(event.target as Node)) {
        handleConfigClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [handleConfigClose]);

  const generateFullPrompt = useCallback((input: string, promptConfig: PromptConfig): string => {
    const toneMap = {
      'creative-funny': 'creatively funny and engaging',
      'basic-info': 'informative and straightforward',
      'deep-research': 'thoroughly researched with detailed cross-checking of facts'
    };

    const lengthMap = {
      'short': 'concise (800-1200 words)',
      'normal': 'standard length (1200-2000 words)',
      'long': 'comprehensive (2000-3500 words)'
    };

    // Include generated title if available and no explicit title exists
    let titleInstruction = '';
    if (generatedTitle && !hasExplicitTitle(input)) {
      titleInstruction = ` Use "${generatedTitle}" as the title.`;
    }

    return `Generate a ${lengthMap[promptConfig.length]} blog post about "${input}" with a ${toneMap[promptConfig.tone]} tone.${titleInstruction} Include relevant examples, actionable insights, and ensure all information is accurate and well-structured.`;
  }, [generatedTitle]);

  const extractTopicFromInput = (input: string): string => {
    // Enhanced topic extraction that looks for key topics and themes
    const cleanInput = input.replace(/^(Generate|Write|Create)\s+(a\s+)?(blog\s+post\s+about\s+|article\s+about\s+)?/i, '').trim();
    
    // Look for quoted topics first
    const quotedMatch = cleanInput.match(/"([^"]+)"/);
    if (quotedMatch) {
      return quotedMatch[1];
    }
    
    // Extract meaningful phrases (noun phrases, key topics)
    const keyTopics = cleanInput.split(/\s+(with|using|including|about|on|for|in|by)\s+/i)[0];
    
    // Take first sentence or meaningful phrase
    const firstSentence = keyTopics.split(/[.!?]/)[0].trim();
    
    if (firstSentence.length <= 60) {
      return firstSentence;
    }
    
    // If too long, take first 50 characters and ensure we don't cut off mid-word
    const truncated = firstSentence.substring(0, 50);
    const lastSpace = truncated.lastIndexOf(' ');
    return lastSpace > 20 ? truncated.substring(0, lastSpace) + '...' : truncated + '...';
  };

  // Check if the input contains an explicit title/topic
  const hasExplicitTitle = (input: string): boolean => {
    // Check for quoted titles first
    if (input.match(/"[^"]+"/)) return true;
    
    // Check for clear title patterns
    const titlePatterns = [
      /^.+:\s*.+/, // "Title: content" pattern
      /^(Title|Topic|Subject):\s*.+/i, // Explicit title declarations
      /^Write about ".*?"/, // "Write about 'title'" pattern
      /^Create.*titled.*["'].+["']/i, // "Create a blog titled 'title'"
    ];
    
    return titlePatterns.some(pattern => pattern.test(input.trim()));
  };

  // Preprocess instructions to extract the core topic for title generation
  const preprocessInstructionsForTitle = (input: string): string => {
    // Remove common instruction prefixes
    let cleaned = input.replace(/^(Generate|Write|Create)\s+(a\s+)?(blog\s+post\s+about\s+|article\s+about\s+|blog\s+about\s+)?/i, '').trim();
    
    // Remove quotes if they wrap the entire content
    cleaned = cleaned.replace(/^["'](.+)["']$/, '$1');
    
    // Take the core content before any additional instructions
    const parts = cleaned.split(/\s+(with|using|including|that|in\s+a|in\s+the\s+style)/i);
    return parts[0].trim();
  };

  // Generate title using LLM when no explicit title is provided
  const generateTitleFromInstructions = async (instructions: string): Promise<string> => {
    try {
      setIsGeneratingTitle(true);
      const preprocessedInstructions = preprocessInstructionsForTitle(instructions);
      const generatedTitle = await blogService.generateTitle(preprocessedInstructions);
      return generatedTitle;
    } catch (error) {
      console.error('Failed to generate title:', error);
      // Fallback to extracted topic
      return extractTopicFromInput(instructions);
    } finally {
      setIsGeneratingTitle(false);
    }
  };

  // Update full instructions and extracted topic when input or config changes
  useEffect(() => {
    if (userInput.trim()) {
      const fullPrompt = generateFullPrompt(userInput.trim(), config);
      setFullInstructions(fullPrompt);
      setExtractedTopic(extractTopicFromInput(userInput.trim()));
    } else {
      setFullInstructions('');
      setExtractedTopic('');
      setGeneratedTitle('');
    }
  }, [userInput, config, generateFullPrompt]);

  // Auto-generate title when input changes and no explicit title is provided
  useEffect(() => {
    const generateTitleAutomatically = async () => {
      if (userInput.trim() && !hasExplicitTitle(userInput.trim())) {
        try {
          setIsGeneratingTitle(true);
          const preprocessedInstructions = preprocessInstructionsForTitle(userInput.trim());
          const title = await blogService.generateTitle(preprocessedInstructions);
          setGeneratedTitle(title);
        } catch (error) {
          console.error('Failed to auto-generate title:', error);
          setGeneratedTitle(extractTopicFromInput(userInput.trim()));
        } finally {
          setIsGeneratingTitle(false);
        }
      } else if (!userInput.trim() || hasExplicitTitle(userInput.trim())) {
        setGeneratedTitle('');
      }
    };

    // Debounce the title generation to avoid too many API calls - wait 5 seconds after user stops typing
    const timeoutId = setTimeout(generateTitleAutomatically, 5000);
    return () => clearTimeout(timeoutId);
  }, [userInput, config]);

  const handleSubmit = async () => {
    if (!userInput.trim() || isGenerating || isGeneratingTitle) return;

    const instructions = fullInstructions || generateFullPrompt(userInput.trim(), config);
    let topic = extractedTopic || extractTopicFromInput(userInput.trim());
    
    // Use the pre-generated title if available, otherwise generate one
    if (!hasExplicitTitle(userInput.trim())) {
      if (generatedTitle) {
        topic = generatedTitle;
      } else {
        try {
          topic = await generateTitleFromInstructions(userInput.trim());
        } catch (error) {
          console.error('Failed to generate title, using fallback:', error);
          // Continue with extracted topic as fallback
        }
      }
    }
    
    try {
      await onGenerate(topic, instructions, config);
      setUserInput('');
      setFullInstructions('');
      setExtractedTopic('');
      setGeneratedTitle('');
      setShowConfig(false);
    } catch (error) {
      console.error('Prompt submission error:', error);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const isDisabled = !userInput.trim() || 
    (!stats || (stats.remainingGenerations <= 0 && stats.monthlyLimit !== -1)) || 
    statsLoading || 
    isGenerating || 
    isGeneratingTitle;

  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Generation limits display */}
      {isFree && stats && (
        <div className="text-center mb-4">
          <p className="text-sm text-gray-600">
            {stats.remainingGenerations} of {stats.monthlyLimit} free generations remaining this month
          </p>
        </div>
      )}

      {/* Error display */}
      {generationError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-sm text-red-700">{generationError}</p>
        </div>
      )}

      {/* Main input container */}
      <div className="relative bg-white border border-gray-200 rounded-2xl shadow-sm focus-within:border-blue-500 focus-within:ring-1 focus-within:ring-blue-500">
        {/* Prompt input */}
        <div className="relative">
          <Textarea
            ref={textareaRef}
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Describe your blog topic and any specific instructions..."
            disabled={isGenerating || isGeneratingTitle}
            className="min-h-[60px] max-h-[300px] resize-none border-0 focus:ring-0 rounded-2xl px-4 py-3 pr-20 text-base leading-relaxed"
            style={{ height: 'auto' }}
          />
          
          {/* Controls container */}
          <div className="absolute bottom-3 right-3 flex items-center gap-2">
            {/* Settings button */}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => showConfig ? handleConfigClose() : setShowConfig(true)}
              className={`h-8 w-8 p-0 rounded-full transition-colors ${
                showConfig ? 'bg-blue-100 text-blue-600' : 'text-gray-400 hover:text-gray-600'
              }`}
            >
              <Settings className="h-4 w-4" />
            </Button>

            {/* Send button */}
            <Button
              onClick={handleSubmit}
              disabled={isDisabled}
              size="sm"
              className="h-8 w-8 p-0 rounded-full"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Configuration panel */}
        {showConfig && (
          <div 
            ref={configRef}
            className="border-t border-gray-200 p-4 space-y-4 animate-in slide-in-from-top-2 duration-200"
          >
            {/* Tone selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Tone</label>
              <div className="flex gap-2">
                {toneOptions.map((option) => (
                  <Button
                    key={option.value}
                    type="button"
                    variant={config.tone === option.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => setConfig({ ...config, tone: option.value })}
                    className="flex-1"
                  >
                    {option.label}
                  </Button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {toneOptions.find(opt => opt.value === config.tone)?.description}
              </p>
            </div>

            {/* Length selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Length</label>
              <div className="flex gap-2">
                {lengthOptions.map((option) => (
                  <Button
                    key={option.value}
                    type="button"
                    variant={config.length === option.value ? "default" : "outline"}
                    size="sm"
                    onClick={() => setConfig({ ...config, length: option.value })}
                    className="flex-1"
                  >
                    {option.label}
                  </Button>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {lengthOptions.find(opt => opt.value === config.length)?.description}
              </p>
            </div>

            {/* Apply Configuration Button */}
            <div className="flex justify-end pt-2 border-t border-gray-200">
              <Button
                type="button"
                onClick={handleConfigClose}
                size="sm"
                className="px-4"
              >
                Apply Configuration
              </Button>
            </div>

            {/* Configuration previews */}
            {fullInstructions && (
              <>
                {/* Generated Title Preview */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {generatedTitle ? 'Generated Title' : 'Extracted Topic'}
                  </label>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                    <p className="text-sm text-blue-800 font-medium leading-relaxed">
                      {generatedTitle || extractedTopic}
                    </p>
                    {isGeneratingTitle && (
                      <div className="flex items-center gap-1 text-xs text-blue-600 mt-1">
                        <div className="animate-spin rounded-full h-3 w-3 border border-blue-600 border-t-transparent"></div>
                        <span>Generating title...</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Full Instructions Preview */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Full Instructions</label>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                    <p className="text-sm text-gray-700 leading-relaxed">{fullInstructions}</p>
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Character counter and status */}
      <div className="flex justify-between items-start mt-2 px-1 gap-4">
        <div className="flex items-center gap-2 flex-wrap">
          <div className="text-xs text-gray-500">
            {userInput.length} characters
          </div>
          
          {/* Title generation status */}
          {isGeneratingTitle && (
            <div className="flex items-center gap-1 text-xs text-blue-600">
              <div className="animate-spin rounded-full h-3 w-3 border border-blue-600 border-t-transparent"></div>
              <span>Generating title...</span>
            </div>
          )}
          
          {/* Generated title preview */}
          {!isGeneratingTitle && generatedTitle && !hasExplicitTitle(userInput.trim()) && (
            <div className="flex items-start gap-1 text-xs text-green-600 min-w-0 flex-1">
              <span className="flex-shrink-0">✓ Generated title:</span>
              {(() => {
                const titleWordCount = generatedTitle.split(/\s+/).length;
                const shouldShowTooltip = titleWordCount > 20;
                
                if (shouldShowTooltip) {
                  return (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span className="font-medium max-w-[300px] truncate cursor-help">
                            {generatedTitle}
                          </span>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-sm p-3">
                          <p className="text-sm">{generatedTitle}</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  );
                } else {
                  return (
                    <span className="font-medium break-words leading-tight">
                      {generatedTitle}
                    </span>
                  );
                }
              })()}
            </div>
          )}
        </div>
        
        {/* Premium upgrade notice */}
        {isFree && stats && stats.remainingGenerations === 0 && (
          <div className="text-xs">
            <span className="text-gray-500 mr-2">Monthly limit reached.</span>
            <Button variant="link" size="sm" className="h-auto p-0 text-xs">
              Upgrade to Premium
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
