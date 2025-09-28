import { afterEach, describe, expect, it } from 'vitest';
import { resetGenerationStore, useGenerationStore } from '@/store/useGenerationStore';
import type { LogEntry } from '@/types/blog';

const sampleLog: LogEntry = {
  timestamp: '2025-09-28T00:00:00.000Z',
  step: 'Test',
  message: 'Processing sample log entry',
  progress: 42,
};

describe('useGenerationStore', () => {
  afterEach(() => {
    resetGenerationStore();
  });

  it('initializes with default state values', () => {
    const state = useGenerationStore.getState();
    expect(state.currentJobId).toBeNull();
    expect(state.isGenerating).toBe(false);
    expect(state.taskLogs).toEqual({});
    expect(state.showDeleteDialog).toBe(false);
  });

  it('updates primitive fields via setter actions', () => {
    const { setCurrentJobId, setIsGenerating, setGenerationError } = useGenerationStore.getState();

    setCurrentJobId('job-123');
    setIsGenerating(true);
    setGenerationError('Failure reason');

    const state = useGenerationStore.getState();
    expect(state.currentJobId).toBe('job-123');
    expect(state.isGenerating).toBe(true);
    expect(state.generationError).toBe('Failure reason');
  });

  it('appends and clears task logs correctly', () => {
    const { appendTaskLog, clearTaskLogs } = useGenerationStore.getState();

    appendTaskLog('task-1', sampleLog);
    appendTaskLog('task-1', { ...sampleLog, message: 'Second entry' });

    let state = useGenerationStore.getState();
    expect(state.taskLogs['task-1']).toHaveLength(2);
    expect(state.taskLogs['task-1'][0].message).toBe('Processing sample log entry');
    expect(state.taskLogs['task-1'][1].message).toBe('Second entry');

    clearTaskLogs();
    state = useGenerationStore.getState();
    expect(state.taskLogs).toEqual({});
  });
});
