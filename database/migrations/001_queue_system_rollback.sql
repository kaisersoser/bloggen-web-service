-- Rollback Migration: Queue System Implementation
-- Date: 2025-11-22
-- Description: Remove queue management fields if deployment needs to be rolled back

-- CAUTION: This will remove queue management data
-- Only run this if you need to rollback the deployment

BEGIN;

-- Drop indexes
DROP INDEX IF EXISTS idx_blogs_queue_position;
DROP INDEX IF EXISTS idx_blogs_status_created;
DROP INDEX IF EXISTS idx_blogs_user_status_created;

-- Remove columns (preserve existing data in other columns)
ALTER TABLE blogs 
  DROP COLUMN IF EXISTS queue_position,
  DROP COLUMN IF EXISTS retry_count,
  DROP COLUMN IF EXISTS max_retries,
  DROP COLUMN IF EXISTS failure_reason,
  DROP COLUMN IF EXISTS last_retry_at;

-- Verify rollback
SELECT 
  column_name, 
  data_type 
FROM information_schema.columns 
WHERE table_name = 'blogs' 
ORDER BY ordinal_position;

COMMIT;

-- After rollback, you should:
-- 1. Revert code to previous version
-- 2. Redeploy backend and frontend
-- 3. Monitor for issues
