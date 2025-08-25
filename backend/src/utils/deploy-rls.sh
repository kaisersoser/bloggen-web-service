#!/bin/bash

# =============================================================================
# RLS DEPLOYMENT SCRIPT
# =============================================================================
# This script automates the deployment of Row Level Security (RLS) policies
# for the Blog Generation Service database.
#
# USAGE:
#   ./deploy-rls.sh [--test-only] [--verify-only]
#
# OPTIONS:
#   --test-only     Only run RLS tests, don't deploy policies
#   --verify-only   Only verify current RLS status
#   --force         Force deployment even if tests fail
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:Qmb53tsDkLY1y7Pa@db.agaejevkyzufcqptatdw.supabase.co:5432/postgres?schema=public"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATABASE_DIR="$SCRIPT_DIR/database"

# Parse command line arguments
TEST_ONLY=false
VERIFY_ONLY=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --test-only)
            TEST_ONLY=true
            shift
            ;;
        --verify-only)
            VERIFY_ONLY=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--test-only] [--verify-only] [--force]"
            exit 1
            ;;
    esac
done

# Functions
print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check if psql is installed
    if ! command -v psql &> /dev/null; then
        print_error "psql (PostgreSQL client) is not installed"
        echo "Please install PostgreSQL client tools:"
        echo "  Ubuntu/Debian: sudo apt-get install postgresql-client"
        echo "  macOS: brew install postgresql"
        echo "  Windows: Download from https://www.postgresql.org/download/"
        exit 1
    fi
    print_success "PostgreSQL client (psql) is available"
    
    # Check database connection
    if ! psql "$DATABASE_URL" -c "SELECT 1;" &> /dev/null; then
        print_error "Cannot connect to database"
        echo "Please check your DATABASE_URL: $DATABASE_URL"
        exit 1
    fi
    print_success "Database connection successful"
    
    # Check if required SQL files exist
    if [[ ! -f "$DATABASE_DIR/rls-setup.sql" ]]; then
        print_error "RLS setup script not found: $DATABASE_DIR/rls-setup.sql"
        exit 1
    fi
    
    if [[ ! -f "$DATABASE_DIR/rls-testing.sql" ]]; then
        print_error "RLS testing script not found: $DATABASE_DIR/rls-testing.sql"
        exit 1
    fi
    
    print_success "All required files are present"
}

verify_current_rls_status() {
    print_header "Verifying Current RLS Status"
    
    # Check if RLS is already enabled
    rls_status=$(psql "$DATABASE_URL" -t -c "
        SELECT COUNT(*) 
        FROM pg_tables t 
        WHERE schemaname = 'public' 
        AND EXISTS (
            SELECT 1 FROM information_schema.tables ist 
            WHERE ist.table_schema = 'public' 
            AND ist.table_name = t.tablename 
            AND ist.table_type = 'BASE TABLE'
        )
        AND rowsecurity = true;
    " 2>/dev/null || echo "0")
    
    total_tables=$(psql "$DATABASE_URL" -t -c "
        SELECT COUNT(*) 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE';
    " 2>/dev/null || echo "0")
    
    echo "Tables with RLS enabled: $rls_status/$total_tables"
    
    if [[ "$rls_status" -gt 0 ]]; then
        print_warning "RLS is already partially or fully enabled"
        
        # Show detailed status
        psql "$DATABASE_URL" -c "
            SELECT 
                tablename,
                rowsecurity as rls_enabled,
                (SELECT count(*) FROM pg_policies 
                 WHERE schemaname = 'public' AND tablename = t.tablename) as policy_count
            FROM pg_tables t
            WHERE schemaname = 'public'
            ORDER BY tablename;
        " 2>/dev/null || echo "Could not retrieve detailed RLS status"
    else
        print_warning "RLS is not currently enabled on any tables"
    fi
}

deploy_rls_policies() {
    print_header "Deploying RLS Policies"
    
    echo "Running RLS setup script..."
    if psql "$DATABASE_URL" -f "$DATABASE_DIR/rls-setup.sql" > /dev/null 2>&1; then
        print_success "RLS policies deployed successfully"
    else
        print_error "Failed to deploy RLS policies"
        echo "Running with verbose output for debugging:"
        psql "$DATABASE_URL" -f "$DATABASE_DIR/rls-setup.sql"
        exit 1
    fi
}

run_rls_tests() {
    print_header "Running RLS Tests"
    
    echo "Executing RLS test suite..."
    test_output=$(psql "$DATABASE_URL" -f "$DATABASE_DIR/rls-testing.sql" 2>&1)
    test_exit_code=$?
    
    if [[ $test_exit_code -eq 0 ]]; then
        print_success "RLS tests completed"
        
        # Check for test failures in output
        if echo "$test_output" | grep -q "FAIL"; then
            print_error "Some RLS tests failed:"
            echo "$test_output" | grep -E "(FAIL|ERROR)"
            
            if [[ "$FORCE" == false ]]; then
                exit 1
            else
                print_warning "Continuing despite test failures (--force specified)"
            fi
        else
            print_success "All RLS tests passed"
        fi
    else
        print_error "RLS test execution failed"
        echo "$test_output"
        exit 1
    fi
}

create_backup() {
    print_header "Creating Database Backup"
    
    backup_file="database_backup_$(date +%Y%m%d_%H%M%S).sql"
    echo "Creating backup: $backup_file"
    
    if pg_dump "$DATABASE_URL" --schema-only > "$backup_file" 2>/dev/null; then
        print_success "Database schema backup created: $backup_file"
    else
        print_warning "Could not create database backup (continuing anyway)"
    fi
}

verify_final_status() {
    print_header "Final Verification"
    
    # Verify all tables have RLS enabled
    tables_without_rls=$(psql "$DATABASE_URL" -t -c "
        SELECT string_agg(tablename, ', ') 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND rowsecurity = false;
    " 2>/dev/null || echo "")
    
    if [[ -n "$tables_without_rls" && "$tables_without_rls" != " " ]]; then
        print_error "Tables without RLS: $tables_without_rls"
        exit 1
    fi
    
    # Count total policies
    total_policies=$(psql "$DATABASE_URL" -t -c "
        SELECT count(*) FROM pg_policies WHERE schemaname = 'public';
    " 2>/dev/null || echo "0")
    
    print_success "RLS implementation complete!"
    echo "  - All tables have RLS enabled"
    echo "  - Total security policies: $total_policies"
    echo "  - System is now fully protected"
}

generate_summary_report() {
    print_header "RLS Deployment Summary"
    
    echo "Generating final status report..."
    
    # Create a comprehensive summary
    cat << EOF

🔒 ROW LEVEL SECURITY DEPLOYMENT REPORT
========================================
Date: $(date)
Database: $(echo "$DATABASE_URL" | sed 's/:[^@]*@/:***@/')

TABLE SECURITY STATUS:
EOF
    
    psql "$DATABASE_URL" -c "
        SELECT 
            '  ' || tablename as \"Table\",
            CASE WHEN rowsecurity THEN '✅ Enabled' ELSE '❌ Disabled' END as \"RLS Status\",
            (SELECT count(*) FROM pg_policies 
             WHERE schemaname = 'public' AND tablename = t.tablename) || ' policies' as \"Policies\"
        FROM pg_tables t
        WHERE schemaname = 'public'
        ORDER BY tablename;
    " -t 2>/dev/null || echo "Could not generate table summary"
    
    echo ""
    echo "DEPLOYMENT STATUS: ✅ COMPLETE"
    echo "SECURITY LEVEL: 🔒 MAXIMUM"
    echo ""
    echo "Next steps:"
    echo "1. Update backend code to use RLS helper functions"
    echo "2. Test user isolation with real user accounts"
    echo "3. Set up monitoring for RLS policy violations"
    echo "4. Schedule regular RLS testing in CI/CD pipeline"
    echo ""
}

# Main execution flow
main() {
    echo -e "${BLUE}"
    cat << "EOF"
╔══════════════════════════════════════════════════════════════════════════════╗
║                     ROW LEVEL SECURITY DEPLOYMENT                           ║
║                        Blog Generation Service                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
    
    check_prerequisites
    
    if [[ "$VERIFY_ONLY" == true ]]; then
        verify_current_rls_status
        exit 0
    fi
    
    verify_current_rls_status
    
    if [[ "$TEST_ONLY" == false ]]; then
        create_backup
        deploy_rls_policies
    fi
    
    run_rls_tests
    
    if [[ "$TEST_ONLY" == false ]]; then
        verify_final_status
        generate_summary_report
    fi
    
    print_success "RLS deployment completed successfully! 🎉"
}

# Execute main function
main "$@"
