-- Fix SECURITY DEFINER functions to resolve Supabase security warnings
-- =============================================================================

-- Drop existing functions with SECURITY DEFINER
DROP FUNCTION IF EXISTS current_user_id();
DROP FUNCTION IF EXISTS is_admin_user();

-- Create safer versions without SECURITY DEFINER
CREATE OR REPLACE FUNCTION current_user_id()
RETURNS TEXT AS $$
BEGIN
  -- Get user ID from JWT claims set by our RLS context
  RETURN COALESCE(
    current_setting('request.jwt.claims', true)::json->>'sub',
    ''
  );
EXCEPTION WHEN OTHERS THEN
  RETURN '';
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION is_admin_user()
RETURNS BOOLEAN AS $$
BEGIN
  -- Check if current user has admin role
  RETURN EXISTS (
    SELECT 1 FROM users 
    WHERE id = current_user_id()
    AND role = 'ADMIN'
  );
EXCEPTION WHEN OTHERS THEN
  RETURN false;
END;
$$ LANGUAGE plpgsql;

-- Verify no more SECURITY DEFINER functions exist
SELECT 
  'SECURITY CLEANUP COMPLETE' as status,
  COUNT(*) as remaining_definer_functions
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND security_type = 'DEFINER'
AND routine_name NOT LIKE 'uuid_%'
AND routine_name NOT LIKE 'gen_%';

SELECT 'Functions recreated without SECURITY DEFINER' as result;
