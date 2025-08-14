-- =============================================================================
-- RLS COVERAGE VERIFICATION SCRIPT
-- =============================================================================
-- This script verifies that our RLS implementation covers ALL tables
-- identified by the Supabase Security Advisor
--
-- Based on Security Advisor findings:
-- ❌ public.blog_logs
-- ❌ public.users  
-- ❌ public.sessions
-- ❌ public.blogs
-- ❌ public.accounts
-- ❌ public.verificationtokens
-- ❌ public.llm_calls
-- ❌ public.audit_sessions
-- =============================================================================

-- Check current RLS status for all tables mentioned in Security Advisor
SELECT 
    'Security Advisor Coverage Check' as check_type,
    tablename,
    CASE 
        WHEN rowsecurity THEN '✅ RLS ENABLED' 
        ELSE '❌ RLS DISABLED' 
    END as current_status,
    (SELECT count(*) FROM pg_policies 
     WHERE schemaname = 'public' AND tablename = t.tablename) as policy_count,
    CASE 
        WHEN tablename IN ('blog_logs', 'users', 'sessions', 'blogs', 'accounts', 'verificationtokens', 'llm_calls', 'audit_sessions') 
        THEN '🎯 REQUIRED BY SECURITY ADVISOR'
        ELSE '📋 Additional Table'
    END as priority
FROM pg_tables t
WHERE schemaname = 'public'
AND tablename IN ('blog_logs', 'users', 'sessions', 'blogs', 'accounts', 'verificationtokens', 'llm_calls', 'audit_sessions')
ORDER BY 
    CASE WHEN rowsecurity THEN 1 ELSE 0 END,
    tablename;

-- Summary of coverage
SELECT 
    'COVERAGE SUMMARY' as summary_type,
    COUNT(*) as total_security_advisor_tables,
    SUM(CASE WHEN rowsecurity THEN 1 ELSE 0 END) as tables_with_rls,
    SUM(CASE WHEN NOT rowsecurity THEN 1 ELSE 0 END) as tables_without_rls,
    CASE 
        WHEN SUM(CASE WHEN NOT rowsecurity THEN 1 ELSE 0 END) = 0 
        THEN '🎉 ALL TABLES SECURED'
        ELSE '⚠️ SECURITY GAPS EXIST'
    END as security_status
FROM pg_tables t
WHERE schemaname = 'public'
AND tablename IN ('blog_logs', 'users', 'sessions', 'blogs', 'accounts', 'verificationtokens', 'llm_calls', 'audit_sessions');

-- Check for any missing tables that exist in database but not in our coverage
SELECT 
    'MISSING TABLES CHECK' as check_type,
    tablename,
    '🤔 NOT IN SECURITY ADVISOR LIST' as status,
    CASE 
        WHEN rowsecurity THEN '✅ Has RLS' 
        ELSE '❌ No RLS' 
    END as rls_status
FROM pg_tables
WHERE schemaname = 'public'
AND tablename NOT IN ('blog_logs', 'users', 'sessions', 'blogs', 'accounts', 'verificationtokens', 'llm_calls', 'audit_sessions')
ORDER BY tablename;

-- Detailed policy breakdown for each required table
SELECT 
    'POLICY DETAILS' as detail_type,
    t.tablename,
    COALESCE(p.policyname, 'NO POLICIES') as policy_name,
    COALESCE(p.cmd, 'N/A') as policy_command,
    CASE 
        WHEN p.policyname IS NULL THEN '❌ NO PROTECTION'
        ELSE '✅ PROTECTED'
    END as protection_status
FROM pg_tables t
LEFT JOIN pg_policies p ON (t.schemaname = p.schemaname AND t.tablename = p.tablename)
WHERE t.schemaname = 'public'
AND t.tablename IN ('blog_logs', 'users', 'sessions', 'blogs', 'accounts', 'verificationtokens', 'llm_calls', 'audit_sessions')
ORDER BY t.tablename, p.policyname;

-- Final verification - should return 0 rows if all is good
SELECT 
    'FINAL VERIFICATION' as verification_type,
    'TABLES WITHOUT RLS' as issue_type,
    tablename,
    '🚨 CRITICAL: IMPLEMENT RLS IMMEDIATELY' as action_required
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN ('blog_logs', 'users', 'sessions', 'blogs', 'accounts', 'verificationtokens', 'llm_calls', 'audit_sessions')
AND NOT rowsecurity;

-- Show success message if all tables are secured
SELECT 
    CASE 
        WHEN (SELECT COUNT(*) FROM pg_tables 
              WHERE schemaname = 'public' 
              AND tablename IN ('blog_logs', 'users', 'sessions', 'blogs', 'accounts', 'verificationtokens', 'llm_calls', 'audit_sessions')
              AND NOT rowsecurity) = 0
        THEN '🎉 SUCCESS: All Security Advisor tables have RLS enabled!'
        ELSE '⚠️ WARNING: Some tables still need RLS implementation'
    END as final_status;
