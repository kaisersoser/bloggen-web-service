// Raw DTO received from backend API (string dates, possibly string error)
export interface ApiBlogDto {
  id: string;
  userId: string;
  topic: string;
  instructions: string | null;
  content: string | null;
  heroImageUrl?: string | null;
  status: string;
  progress?: number;
  currentStep?: string | null;
  error?: string | object | null;
  createdAt: string; // ISO
  updatedAt: string; // ISO
  completedAt?: string | null; // ISO
}

// Normalized BlogData used across the frontend (string timestamps for portability)
export interface BlogData {
  id: string;
  userId: string;
  topic: string;
  instructions: string | null;
  content: string | null;
  heroImageUrl?: string | null;
  status: string;
  progress: number;
  currentStep: string | null;
  error: ErrorInfo | null;
  createdAt: string; // ISO
  updatedAt: string; // ISO
  completedAt: string | null; // ISO or null
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
  hero_image_url?: string;
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

// Mapper: normalize API blog DTO -> BlogData
export function mapApiBlog(dto: ApiBlogDto): BlogData {
  let normalizedError: ErrorInfo | null = null;
  if (dto.error) {
    if (typeof dto.error === 'string') {
      normalizedError = {
        error_type: 'generation_error',
        user_message: dto.error,
        technical_details: dto.error,
        is_recoverable: false,
        suggestions: [],
        timestamp: new Date().toISOString(),
        severity: 'error'
      };
    } else if (typeof dto.error === 'object') {
      const e: any = dto.error;
      normalizedError = {
        error_type: e.error_type || 'generation_error',
        user_message: e.user_message || 'An error occurred',
        technical_details: e.technical_details || JSON.stringify(e),
        is_recoverable: !!e.is_recoverable,
        suggestions: Array.isArray(e.suggestions) ? e.suggestions : [],
        timestamp: e.timestamp || new Date().toISOString(),
        severity: e.severity || 'error'
      };
    }
  }

  return {
    id: dto.id,
    userId: dto.userId,
    topic: dto.topic,
    instructions: dto.instructions,
    content: dto.content,
  heroImageUrl: dto.heroImageUrl ?? null,
    status: dto.status,
    progress: dto.progress ?? 0,
    currentStep: dto.currentStep || null,
    error: normalizedError,
    createdAt: dto.createdAt,
    updatedAt: dto.updatedAt,
    completedAt: dto.completedAt || null
  };
}
