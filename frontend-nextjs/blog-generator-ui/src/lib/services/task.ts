// src/lib/services/task.ts
import { api } from '../api-client';
import { JobState } from '@/types/blog';
import { logger } from '@/lib/logger';

interface TaskStatus {
  id: string;
  topic: string;
  status: string;
  created_at: string;
  current_step: string;
  result?: string;
  error?: string;
  user_id: string;
  user_email: string;
  user_role: string;
}

class TaskService {
  async getTaskStatus(taskId: string): Promise<TaskStatus | null> {
    try {
      const response = await api.tasks.getStatus(taskId);
      if (!response.success) {
        return null;
      }
      return response.data as TaskStatus;
    } catch (error) {
      logger.error('Error fetching task status', { error, taskId });
      return null;
    }
  }

  async getActiveTasks(): Promise<TaskStatus[]> {
    try {
      const response = await api.tasks.getActiveTasks();
      if (!response.success) {
        return [];
      }
      return (response.data as { tasks: TaskStatus[] }).tasks || [];
    } catch {
      // If endpoint doesn't exist yet, return empty array
      return [];
    }
  }

  // Convert TaskStatus from backend to JobState for frontend
  convertTaskToJob(task: TaskStatus): JobState {
    return {
      id: task.id,
      topic: task.topic,
      instructions: '', // Not available in task status
      status: this.mapTaskStatus(task.status),
      progress: this.getProgressFromStatus(task.status),
      currentStep: task.current_step,
      logs: [],
      blogContent: task.result || '',
      error: task.error ? {
        error_type: 'generation_error',
        user_message: task.error,
        technical_details: task.error,
        is_recoverable: true,
        suggestions: ['Try refreshing the page', 'Contact support if issue persists'],
        timestamp: new Date().toISOString(),
        severity: 'error'
      } : null,
      createdAt: task.created_at,
      completedAt: task.status === 'completed' ? new Date().toISOString() : undefined
    };
  }

  private mapTaskStatus(status: string): JobState['status'] {
    switch (status) {
      case 'in_progress':
        return 'in_progress';
      case 'completed':
        return 'completed';
      case 'failed':
        return 'failed';
      default:
        return 'queued';
    }
  }

  private getProgressFromStatus(status: string): number {
    switch (status) {
      case 'queued':
        return 0;
      case 'in_progress':
        return 50;
      case 'completed':
        return 100;
      case 'failed':
        return 0;
      default:
        return 0;
    }
  }
}

export const taskService = new TaskService();
