-- =============================================================================
-- CORRECTED RLS SETUP SCRIPT WITH PROPER COLUMN NAMES
-- =============================================================================
-- This script uses the actual database column names (snake_case)
-- Based on the real schema inspection from Supabase

-- Create the missing policies with correct column names
-- =============================================================================

-- Accounts table: Users can only access their own OAuth accounts
DROP POLICY IF EXISTS "accounts_own_data" ON accounts;
CREATE POLICY "accounts_own_data" ON accounts
FOR ALL USING (
  current_user_id() = user_id OR 
  is_admin_user()
);

-- Sessions table: Users can only access their own active sessions
DROP POLICY IF EXISTS "sessions_own_data" ON sessions;
CREATE POLICY "sessions_own_data" ON sessions
FOR ALL USING (
  current_user_id() = user_id OR 
  is_admin_user()
);

-- Blogs table: Users can only access their own blogs
DROP POLICY IF EXISTS "blogs_own_data" ON blogs;
CREATE POLICY "blogs_own_data" ON blogs
FOR ALL USING (
  current_user_id() = user_id OR 
  is_admin_user()
);

-- Audit sessions: Users can only access their own usage analytics
DROP POLICY IF EXISTS "audit_sessions_own_data" ON audit_sessions;
CREATE POLICY "audit_sessions_own_data" ON audit_sessions
FOR ALL USING (
  current_user_id() = user_id OR 
  is_admin_user()
);

-- Protect audit history: Prevent deletion of records older than 90 days
DROP POLICY IF EXISTS "audit_sessions_delete_protection" ON audit_sessions;
CREATE POLICY "audit_sessions_delete_protection" ON audit_sessions
FOR DELETE USING (
  (end_time IS NULL OR end_time > NOW() - INTERVAL '90 days') OR
  is_admin_user()
);

-- LLM calls: Access only through owned audit sessions
DROP POLICY IF EXISTS "llm_calls_own_data" ON llm_calls;
CREATE POLICY "llm_calls_own_data" ON llm_calls
FOR ALL USING (
  EXISTS (
    SELECT 1 FROM audit_sessions 
    WHERE id = llm_calls.audit_session_id 
    AND (user_id = current_user_id() OR is_admin_user())
  )
);

-- Check if blog_logs table exists and create policy
DO $$
BEGIN
  IF EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'blog_logs') THEN
    -- Blog logs: Users can only access logs for their own blogs
    EXECUTE 'DROP POLICY IF EXISTS "blog_logs_own_data" ON blog_logs';
    EXECUTE 'CREATE POLICY "blog_logs_own_data" ON blog_logs
    FOR ALL USING (
      EXISTS (
        SELECT 1 FROM blogs 
        WHERE id = blog_logs.blog_id 
        AND (user_id = current_user_id() OR is_admin_user())
      )
    )';
    RAISE NOTICE 'Created policy for blog_logs table';
  ELSE
    RAISE NOTICE 'blog_logs table does not exist, skipping policy creation';
  END IF;
END
$$;

-- Show final policy status
SELECT 
  'POLICY CREATION COMPLETE' as status,
  tablename,
  (SELECT count(*) FROM pg_policies WHERE schemaname = 'public' AND tablename = t.tablename) as policy_count
FROM pg_tables t
WHERE schemaname = 'public'
AND tablename IN ('accounts', 'sessions', 'blogs', 'audit_sessions', 'llm_calls', 'blog_logs', 'users', 'verificationtokens')
ORDER BY tablename;
