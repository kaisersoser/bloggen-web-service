export interface BlogData {
  id: string
  userId: string
  topic: string
  instructions: string | null
  content: string | null
  status: string
  progress: number
  currentStep: string | null
  error: string | null
  createdAt: Date
  updatedAt: Date
  completedAt: Date | null
}

export interface BlogGenerationResponse {
  task_id: string;
  message?: string;
}

export interface JobState {
  id: string;
  topic: string;
  instructions: string;
  status: 'queued' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  currentStep: string;
  logs: LogUpdate[];
  blogContent: string;
  error: ErrorInfo | null;
  createdAt: string;
  completedAt?: string;
}

export interface SSEUpdate {
  type: 'connected' | 'status_update' | 'log_update' | 'stream_ended' | 'error';
  task_id: string;
  status?: string;
  current_step?: string;
  progress?: number;
  result?: string;
  error?: string;
  message?: string;
  timestamp?: string;
  step?: string;
}

export interface LogEntry {
  timestamp: string;
  step: string;
  message: string;
  progress: number;
}

export interface LogUpdate {
  task_id: string;
  log: string;
  timestamp: string;
}

export interface ErrorInfo {
  error_type: string;
  user_message: string;
  technical_details: string;
  is_recoverable: boolean;
  suggestions: string[];
  timestamp: string;
  severity: string;
}

export interface SelectionState {
  isSelectionMode: boolean;
  selectedBlogIds: Set<string>;
  longPressTimer: NodeJS.Timeout | null;
  targetBlogId: string | null;
  pulsingBlogId: string | null;
}
