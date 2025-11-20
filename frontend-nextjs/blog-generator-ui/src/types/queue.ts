// Queue-related type definitions for async blog generation

export interface QueueStatus {
  currentJob: {
    taskId: string;
    topic: string;
    progress: number;
    startedAt: string;
  } | null;
  queuedCount: number;
  userQueuedCount: number;
  estimatedWaitMinutes: number;
  isProcessing: boolean;
  statistics: {
    totalProcessed: number;
    totalFailed: number;
    averageDurationSeconds: number;
  };
}

export interface GenerationLog {
  timestamp: string;
  step: string;
  message: string;
  progress: number;
  level: 'info' | 'warning' | 'error' | 'success';
}

export interface DraftContent {
  sections: Record<string, string>; // section name -> content
  progress: number;
  updatedAt: string;
  metadata?: {
    title?: string;
    heroImageUrl?: string;
  };
}

export interface QueueBlogData {
  id: string;
  userId: string;
  topic: string;
  instructions: string | null;
  status: 'QUEUED' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  progress: number;
  queuePosition: number | null;
  retryCount: number;
  maxRetries: number;
  failureReason: string | null;
  createdAt: string;
  completedAt: string | null;
  lastRetryAt: string | null;
}
