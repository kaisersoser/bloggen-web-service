import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';

interface BlogGenerationFormProps {
  onGenerate: (topic: string, instructions: string) => Promise<void>;
  stats: {
    remainingGenerations: number;
    monthlyLimit: number;
  } | null;
  isFree: boolean;
  generationError: string | null;
  statsLoading: boolean;
}

export function BlogGenerationForm({
  onGenerate,
  stats,
  isFree,
  generationError,
  statsLoading
}: BlogGenerationFormProps) {
  const [topic, setTopic] = useState('');
  const [instructions, setInstructions] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleSubmit = async () => {
    if (!topic.trim() || isGenerating) return;

    try {
      setIsGenerating(true);
      await onGenerate(topic.trim(), instructions.trim());
      // Clear form on successful submission
      setTopic('');
      setInstructions('');
    } catch (error) {
      // Error handling is done in parent component
      console.error('Form submission error:', error);
    } finally {
      setIsGenerating(false);
    }
  };

  const isDisabled = !topic.trim() || 
    (!stats || (stats.remainingGenerations <= 0 && stats.monthlyLimit !== -1)) || 
    statsLoading || 
    isGenerating;

  const buttonText = !stats 
    ? 'Loading...' 
    : isGenerating
    ? 'Generating...'
    : (stats.remainingGenerations > 0 || stats.monthlyLimit === -1) 
    ? 'Generate Blog' 
    : 'Monthly Limit Reached';

  return (
    <Card>
      <CardHeader>
        <CardTitle>Generate New Blog</CardTitle>
        {isFree && stats && (
          <p className="text-sm text-gray-600">
            {stats.remainingGenerations} of {stats.monthlyLimit} free generations remaining this month
          </p>
        )}
        {isFree && !stats && (
          <p className="text-sm text-gray-600">
            Loading generation limits...
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {generationError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-sm text-red-700">{generationError}</p>
          </div>
        )}
        
        <div>
          <label className="block text-sm font-medium mb-2">Blog Topic</label>
          <Input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter your blog topic..."
            className="w-full"
            disabled={isGenerating}
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-2">Additional Instructions (Optional)</label>
          <Textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="Any specific requirements or style preferences..."
            className="min-h-[100px]"
            disabled={isGenerating}
          />
        </div>
        
        <Button
          onClick={handleSubmit}
          disabled={isDisabled}
          className="w-full"
        >
          {buttonText}
        </Button>
        
        {isFree && stats && stats.remainingGenerations === 0 && (
          <div className="text-center">
            <p className="text-sm text-gray-600 mb-2">
              Upgrade to Premium for unlimited blog generation
            </p>
            <Button variant="outline" size="sm">
              Upgrade Now
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
