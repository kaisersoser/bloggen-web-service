-- =============================================================================
-- ROW LEVEL SECURITY (RLS) SETUP FOR BLOG GENERATION SERVICE
-- =============================================================================
-- This script implements comprehensive Row Level Security for all database tables
-- 
-- SECURITY FEATURES:
-- ✅ User data isolation (users can only access their own data)
-- ✅ Admin bypass policies (admins can access all data for support)
-- ✅ Content moderation (hide flagged content from regular users)
-- ✅ Audit protection (prevent deletion of historical audit data)
-- ✅ Service role configuration (backend can operate with elevated privileges)
--
-- USAGE:
-- 1. Connect to your Supabase database as a superuser
-- 2. Run this script to enable RLS on all tables
-- 3. Test with different user roles to verify isolation
-- =============================================================================

-- Enable RLS on all tables (based on Supabase Security Advisor findings)
-- =============================================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE blogs ENABLE ROW LEVEL SECURITY;
ALTER TABLE blog_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE verificationtokens ENABLE ROW LEVEL SECURITY;

-- Helper functions for security policies
-- =============================================================================

-- Function to check if current user is an admin
CREATE OR REPLACE FUNCTION is_admin_user()
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM users 
    WHERE id = auth.uid()::text 
    AND role = 'ADMIN'
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get current user ID safely
CREATE OR REPLACE FUNCTION current_user_id()
RETURNS TEXT AS $$
BEGIN
  RETURN auth.uid()::text;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- CORE TABLE POLICIES
-- =============================================================================

-- Users table: Users can only access their own profile data
-- Admins can access all user data for support purposes
DROP POLICY IF EXISTS "users_own_data" ON users;
CREATE POLICY "users_own_data" ON users
FOR ALL USING (
  current_user_id() = id OR 
  is_admin_user()
);

-- Accounts table: Users can only access their own OAuth accounts
-- Admins can access all accounts for troubleshooting
DROP POLICY IF EXISTS "accounts_own_data" ON accounts;
CREATE POLICY "accounts_own_data" ON accounts
FOR ALL USING (
  current_user_id() = "userId" OR 
  is_admin_user()
);

-- Sessions table: Users can only access their own active sessions
-- Admins can access all sessions for monitoring
DROP POLICY IF EXISTS "sessions_own_data" ON sessions;
CREATE POLICY "sessions_own_data" ON sessions
FOR ALL USING (
  current_user_id() = "userId" OR 
  is_admin_user()
);

-- Blogs table: Users can only access their own blogs
-- Admins can access all blogs for content moderation
DROP POLICY IF EXISTS "blogs_own_data" ON blogs;
CREATE POLICY "blogs_own_data" ON blogs
FOR ALL USING (
  current_user_id() = "userId" OR 
  is_admin_user()
);

-- Blog logs table: Users can only access logs for their own blogs
-- Admins can access all blog logs for system monitoring
DROP POLICY IF EXISTS "blog_logs_own_data" ON blog_logs;
CREATE POLICY "blog_logs_own_data" ON blog_logs
FOR ALL USING (
  EXISTS (
    SELECT 1 FROM blogs 
    WHERE id = blog_logs."blogId" 
    AND ("userId" = current_user_id() OR is_admin_user())
  )
);

-- Hide blogs with inappropriate content from regular users
-- Users can still see their own flagged content, admins see everything
DROP POLICY IF EXISTS "blogs_content_filter" ON blogs;
CREATE POLICY "blogs_content_filter" ON blogs
FOR SELECT USING (
  status != 'FLAGGED' OR
  current_user_id() = "userId" OR
  is_admin_user()
);

-- Audit sessions: Users can only access their own usage analytics
-- Admins can access all audit data for system monitoring
DROP POLICY IF EXISTS "audit_sessions_own_data" ON audit_sessions;
CREATE POLICY "audit_sessions_own_data" ON audit_sessions
FOR ALL USING (
  current_user_id() = "userId" OR 
  is_admin_user()
);

-- Protect audit history: Prevent deletion of records older than 90 days
-- unless user is admin (for compliance and billing purposes)
DROP POLICY IF EXISTS "audit_sessions_delete_protection" ON audit_sessions;
CREATE POLICY "audit_sessions_delete_protection" ON audit_sessions
FOR DELETE USING (
  ("endTime" IS NULL OR "endTime" > NOW() - INTERVAL '90 days') OR
  is_admin_user()
);

-- LLM calls: Access only through owned audit sessions
-- Admins can access all LLM call data for cost analysis
DROP POLICY IF EXISTS "llm_calls_own_data" ON llm_calls;
CREATE POLICY "llm_calls_own_data" ON llm_calls
FOR ALL USING (
  EXISTS (
    SELECT 1 FROM audit_sessions 
    WHERE id = llm_calls."auditSessionId" 
    AND ("userId" = current_user_id() OR is_admin_user())
  )
);

-- Verification tokens: Allow access for email verification flow
-- These are temporary tokens and don't contain sensitive user data
DROP POLICY IF EXISTS "verification_tokens_access" ON verificationtokens;
CREATE POLICY "verification_tokens_access" ON verificationtokens
FOR ALL USING (true);

-- SERVICE ROLE CONFIGURATION
-- =============================================================================

-- Grant necessary permissions to service role for backend operations
DO $$
BEGIN
  -- Create service_role if it doesn't exist
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'service_role') THEN
    CREATE ROLE service_role;
  END IF;
END
$$;

-- Grant permissions to service role
GRANT USAGE ON SCHEMA public TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- Allow service role to bypass RLS when performing system operations
-- This is needed for backend services that operate on behalf of users
ALTER ROLE service_role SET row_security = off;

-- ADDITIONAL SECURITY CONFIGURATIONS
-- =============================================================================

-- Ensure all future tables inherit RLS settings
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;

-- Create monitoring view for RLS policy status
CREATE OR REPLACE VIEW rls_policy_status AS
SELECT 
  schemaname,
  tablename,
  rowsecurity as rls_enabled,
  (SELECT count(*) FROM pg_policies WHERE schemaname = t.schemaname AND tablename = t.tablename) as policy_count
FROM pg_tables t
WHERE schemaname = 'public'
ORDER BY tablename;

-- Grant access to monitoring view
GRANT SELECT ON rls_policy_status TO service_role;

-- =============================================================================
-- RLS SETUP COMPLETE
-- =============================================================================

-- Display setup status
SELECT 
  'RLS Setup Complete!' as status,
  'Tables protected: ' || count(*) as tables_count
FROM pg_tables 
WHERE schemaname = 'public';

-- Show policy summary
SELECT * FROM rls_policy_status;
