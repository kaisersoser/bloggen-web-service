-- Migration: Queue System Implementation
-- Date: 2025-11-22
-- Description: Add queue management fields to blogs table for sequential generation

-- Add new columns to blogs table (if they don't exist)
ALTER TABLE blogs 
  ADD COLUMN IF NOT EXISTS queue_position INTEGER,
  ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0 NOT NULL,
  ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3 NOT NULL,
  ADD COLUMN IF NOT EXISTS failure_reason TEXT,
  ADD COLUMN IF NOT EXISTS last_retry_at TIMESTAMP WITH TIME ZONE;

-- Create indexes for queue management
CREATE INDEX IF NOT EXISTS idx_blogs_queue_position ON blogs(queue_position);
CREATE INDEX IF NOT EXISTS idx_blogs_status_created ON blogs(status, created_at);
CREATE INDEX IF NOT EXISTS idx_blogs_user_status_created ON blogs(user_id, status, created_at);

-- Update any existing IN_PROGRESS blogs to QUEUED (in case of stuck jobs)
-- This ensures a clean slate for the queue system
UPDATE blogs 
SET status = 'QUEUED', 
    queue_position = NULL,
    updated_at = NOW()
WHERE status = 'IN_PROGRESS';

-- Verify changes
SELECT 
  'blogs' as table_name,
  COUNT(*) as total_rows,
  COUNT(*) FILTER (WHERE status = 'QUEUED') as queued_count,
  COUNT(*) FILTER (WHERE status = 'IN_PROGRESS') as in_progress_count,
  COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed_count,
  COUNT(*) FILTER (WHERE status = 'FAILED') as failed_count
FROM blogs;

COMMENT ON COLUMN blogs.queue_position IS 'Position in generation queue (NULL = not queued)';
COMMENT ON COLUMN blogs.retry_count IS 'Number of retry attempts for failed generations';
COMMENT ON COLUMN blogs.max_retries IS 'Maximum allowed retry attempts';
COMMENT ON COLUMN blogs.failure_reason IS 'Detailed reason for generation failure';
COMMENT ON COLUMN blogs.last_retry_at IS 'Timestamp of last retry attempt';
