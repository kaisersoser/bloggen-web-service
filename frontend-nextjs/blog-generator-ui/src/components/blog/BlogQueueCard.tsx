"use client";

import React from 'react';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { QueueStatusBadge } from './QueueStatusBadge';
import { Eye, RefreshCw, Trash2, FileText, Clock } from 'lucide-react';
import { QueueBlogData } from '@/types/queue';
import { formatDistanceToNow } from 'date-fns';

interface BlogQueueCardProps {
  blog: QueueBlogData;
  onViewLogs?: (taskId: string) => void;
  onViewDraft?: (taskId: string) => void;
  onRetry?: (taskId: string) => void;
  onDelete?: (taskId: string) => void;
  onViewContent?: (blog: QueueBlogData) => void;
}

export const BlogQueueCard: React.FC<BlogQueueCardProps> = ({
  blog,
  onViewLogs,
  onViewDraft,
  onRetry,
  onDelete,
  onViewContent,
}) => {
  const canRetry = blog.status === 'FAILED' && blog.retryCount < blog.maxRetries;
  const canViewDraft = blog.status === 'IN_PROGRESS';
  const canViewContent = blog.status === 'COMPLETED';
  const canViewLogs = blog.status === 'IN_PROGRESS' || blog.status === 'FAILED';

  const getTimeDisplay = () => {
    if (blog.completedAt) {
      return `Completed ${formatDistanceToNow(new Date(blog.completedAt), { addSuffix: true })}`;
    }
    return `Created ${formatDistanceToNow(new Date(blog.createdAt), { addSuffix: true })}`;
  };

  const getWaitEstimate = () => {
    if (blog.status === 'QUEUED' && blog.queuePosition) {
      // Rough estimate: 2-3 minutes per job
      const estimatedMinutes = blog.queuePosition * 2.5;
      if (estimatedMinutes < 60) {
        return `~${Math.round(estimatedMinutes)} min wait`;
      }
      return `~${Math.round(estimatedMinutes / 60)} hr wait`;
    }
    return null;
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-lg truncate">{blog.topic}</h3>
            {blog.instructions && (
              <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                {blog.instructions}
              </p>
            )}
          </div>
          <QueueStatusBadge
            status={blog.status}
            queuePosition={blog.queuePosition}
            retryCount={blog.retryCount}
            progress={blog.progress}
          />
        </div>
      </CardHeader>

      <CardContent className="pb-3">
        {/* Progress bar for in-progress blogs */}
        {blog.status === 'IN_PROGRESS' && (
          <div className="space-y-2">
            <ProgressBar value={blog.progress} className="h-2" showLabel={false} />
            <p className="text-xs text-muted-foreground">
              Generating blog content... {blog.progress}%
            </p>
          </div>
        )}

        {/* Wait estimate for queued blogs */}
        {blog.status === 'QUEUED' && getWaitEstimate() && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>{getWaitEstimate()}</span>
          </div>
        )}

        {/* Failure reason */}
        {blog.status === 'FAILED' && blog.failureReason && (
          <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-md p-3">
            <p className="text-sm text-red-800 dark:text-red-200 font-medium mb-1">
              Generation Failed
            </p>
            <p className="text-xs text-red-600 dark:text-red-300">
              {blog.failureReason}
            </p>
            {canRetry && (
              <p className="text-xs text-muted-foreground mt-2">
                Retry {blog.retryCount} of {blog.maxRetries} used
              </p>
            )}
          </div>
        )}

        {/* Timestamp */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-3">
          <Clock className="h-3.5 w-3.5" />
          <span>{getTimeDisplay()}</span>
        </div>
      </CardContent>

      <CardFooter className="pt-3 border-t flex gap-2 justify-end">
        {/* View Content (completed) */}
        {canViewContent && onViewContent && (
          <Button
            variant="default"
            size="sm"
            onClick={() => onViewContent(blog)}
            className="gap-2"
          >
            <Eye className="h-4 w-4" />
            View Blog
          </Button>
        )}

        {/* View Draft (in progress) */}
        {canViewDraft && onViewDraft && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onViewDraft(blog.id)}
            className="gap-2"
          >
            <FileText className="h-4 w-4" />
            Preview Draft
          </Button>
        )}

        {/* View Logs (in progress or failed) */}
        {canViewLogs && onViewLogs && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onViewLogs(blog.id)}
            className="gap-2"
          >
            <Eye className="h-4 w-4" />
            View Logs
          </Button>
        )}

        {/* Retry (failed with retries left) */}
        {canRetry && onRetry && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onRetry(blog.id)}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
        )}

        {/* Delete */}
        {onDelete && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(blog.id)}
            className="gap-2 text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </CardFooter>
    </Card>
  );
};

export default BlogQueueCard;
