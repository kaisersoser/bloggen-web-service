# 🔒 Row Level Security (RLS) Implementation Guide

## 📋 **Implementation Checklist**

### ✅ **Phase 1: Database Setup** (Critical - 2 hours)

**1.1 Run RLS Setup Script**
```bash
# Connect to your Supabase database and run the setup script
psql "postgresql://postgres:[YOUR_NEW_PASSWORD]@db.agaejevkyzufcqptatdw.supabase.co:5432/postgres?schema=public" < database/rls-setup.sql
```

**1.2 Verify RLS Status**
```bash
# Run the testing script to verify all policies work correctly
psql "postgresql://postgres:[YOUR_NEW_PASSWORD]@db.agaejevkyzufcqptatdw.supabase.co:5432/postgres?schema=public" < database/rls-testing.sql
```

**1.3 Check Policy Summary**
```sql
-- View RLS status for all tables
SELECT * FROM rls_policy_status;

-- Should show:
-- users: rls_enabled=true, policy_count=1
-- blogs: rls_enabled=true, policy_count=2  
-- blog_logs: rls_enabled=true, policy_count=1
-- audit_sessions: rls_enabled=true, policy_count=2
-- llm_calls: rls_enabled=true, policy_count=1
-- accounts: rls_enabled=true, policy_count=1
-- sessions: rls_enabled=true, policy_count=1
-- verificationtokens: rls_enabled=true, policy_count=1
```

### ✅ **Phase 2: Backend Integration** (1 hour)

**2.1 Update Backend Dependencies**
```bash
cd backend
pip install asyncpg  # If not already installed
```

**2.2 Use RLS Helper in API Endpoints**
```python
# Example: Update blog endpoints to use RLS
from core.rls_helper import RLSHelper, get_user_blogs_rls

@app.get("/my-blogs")
async def get_my_blogs(user: User = Depends(get_current_user)):
    # This automatically enforces RLS - user can only see their own blogs
    blogs = await get_user_blogs_rls(user.id)
    return {"blogs": blogs}

@app.get("/admin/all-blogs")  
async def get_all_blogs_admin(user: User = Depends(require_admin)):
    # Admin endpoint that bypasses RLS
    async with RLSHelper.service_context() as conn:
        blogs = await conn.fetch("SELECT * FROM blogs ORDER BY created_at DESC")
    return {"blogs": [dict(row) for row in blogs]}
```

**2.3 Update Existing Database Queries**
```python
# OLD: Direct database queries (not RLS-protected)
blogs = await database.fetch_all("SELECT * FROM blogs WHERE userId = :user_id", {"user_id": user.id})

# NEW: RLS-protected queries (automatic user isolation)
async with RLSHelper.user_context(user.id) as conn:
    blogs = await conn.fetch("SELECT * FROM blogs")  # Only returns user's blogs
```

### ✅ **Phase 3: Testing & Validation** (30 minutes)

**3.1 Run Automated RLS Tests**
```python
# Test script to verify RLS isolation
from core.rls_helper import RLSHelper

async def test_rls_implementation():
    # Test user isolation
    results = await RLSHelper.test_user_isolation("test_user_1_id", "test_user_2_id")
    print("User Isolation Test:", results)
    
    # Verify RLS setup
    status = await RLSHelper.verify_rls_setup()
    print("RLS Setup Status:", status)
    
    return results["isolation_verified"] and "error" not in status

# Run the test
if await test_rls_implementation():
    print("✅ RLS implementation successful!")
else:
    print("❌ RLS implementation needs fixes")
```

**3.2 Manual Security Testing**
```bash
# Test 1: Regular user should only see their own data
psql -c "SELECT set_config('request.jwt.claims', '{\"sub\": \"test_user_1_id\"}', true); SELECT COUNT(*) FROM blogs;"

# Test 2: Admin user should see all data  
psql -c "SELECT set_config('request.jwt.claims', '{\"sub\": \"test_admin_id\"}', true); SELECT COUNT(*) FROM blogs;"

# Test 3: Verify flagged content is hidden
psql -c "SELECT set_config('request.jwt.claims', '{\"sub\": \"test_user_2_id\"}', true); SELECT COUNT(*) FROM blogs WHERE status = 'FLAGGED';"
```

## 🛡️ **Security Policies Overview**

### **Table-Level Protection**

| Table | RLS Enabled | User Access | Admin Access | Notes |
|-------|-------------|-------------|--------------|-------|
| `users` | ✅ | Own profile only | All profiles | User management |
| `blogs` | ✅ | Own blogs only | All blogs | Content isolation |
| `blog_logs` | ✅ | Own blog logs only | All logs | Debug/audit logs |
| `audit_sessions` | ✅ | Own usage only | All usage | Cost tracking |
| `llm_calls` | ✅ | Through owned audits | All calls | API usage logs |
| `accounts` | ✅ | Own OAuth accounts | All accounts | Authentication |
| `sessions` | ✅ | Own sessions | All sessions | Session management |
| `verificationtokens` | ✅ | Public access | Public access | Email verification |

### **Policy Details**

**Users Table:**
- `users_own_data`: Users can only access their own profile
- Admin bypass for user management and support

**Blogs Table:**
- `blogs_own_data`: Users can only access their own blogs  
- `blogs_content_filter`: Hide flagged content from non-owners
- Admin bypass for content moderation

**Blog Logs Table:**
- `blog_logs_own_data`: Users can only access logs for their own blogs
- Inherited security through blog ownership relationship
- Admin bypass for system debugging and monitoring

**Audit Sessions:**
- `audit_sessions_own_data`: Users can only access their own usage data
- `audit_sessions_delete_protection`: Prevent deletion of historical data (90+ days)
- Admin bypass for analytics and billing

## 📊 **Benefits & Impact**

### **Security Improvements**
- ✅ **Database-level isolation**: Even if application logic fails, users cannot access other users' data
- ✅ **Admin accountability**: Clear separation between user and admin operations
- ✅ **Content moderation**: Automatic hiding of inappropriate content
- ✅ **Audit protection**: Historical data preserved for compliance

### **Performance Impact**
- ⚡ **Minimal overhead**: RLS policies are very efficient (index-based filtering)
- ⚡ **Query optimization**: PostgreSQL optimizes RLS queries automatically
- ⚡ **No application changes**: Existing queries work with automatic filtering

### **Compliance Benefits**
- 🔒 **GDPR compliance**: Users can only access their own personal data
- 🔒 **SOC 2 Type II**: Database-level access controls documented
- 🔒 **HIPAA ready**: If health data is added, isolation is already enforced
- 🔒 **Financial auditing**: Cost tracking data is user-isolated and protected

## 🚨 **Critical Security Notes**

### **Service Role Usage**
```python
# ✅ GOOD: Use service context for legitimate admin operations
async with RLSHelper.service_context() as conn:
    # System maintenance, analytics, admin functions
    cleanup_old_data()

# ❌ BAD: Never use service context for user-facing operations
async with RLSHelper.service_context() as conn:
    return await get_user_blogs()  # This bypasses security!
```

### **User Context Verification**
```python
# ✅ GOOD: Always use authenticated user ID
user = await get_current_user(token)
async with RLSHelper.user_context(user.id) as conn:
    blogs = await conn.fetch("SELECT * FROM blogs")

# ❌ BAD: Never trust user-provided IDs
user_id = request.json.get("user_id")  # User could specify any ID!
async with RLSHelper.user_context(user_id) as conn:  # Security violation!
    blogs = await conn.fetch("SELECT * FROM blogs")
```

### **Testing Requirements**
- 🧪 **Required**: Run RLS tests before each deployment
- 🧪 **Required**: Verify user isolation with different test accounts  
- 🧪 **Required**: Test admin bypass functionality
- 🧪 **Required**: Validate content filtering for flagged items

## 🔧 **Deployment Commands**

```bash
# 1. Enable RLS on database
make rls-setup

# 2. Run RLS tests
make rls-test

# 3. Update backend with RLS integration
make backend-update-rls

# 4. Deploy with RLS verification
make deploy-with-rls-check
```

## 📞 **Support & Troubleshooting**

### **Common Issues**

**Issue**: Users can't see their own data
**Solution**: Check if user context is being set correctly
```sql
-- Debug user context
SELECT current_setting('request.jwt.claims', true);
-- Should return: {"sub": "actual_user_id"}
```

**Issue**: Admin can't access all data
**Solution**: Verify admin role detection
```sql
-- Test admin detection
SELECT is_admin_user();
-- Should return: true for admin users
```

**Issue**: RLS policies not working
**Solution**: Verify RLS is enabled
```sql
-- Check RLS status
SELECT * FROM rls_policy_status WHERE NOT rls_enabled;
-- Should return: no rows (all tables should have RLS enabled)
```

### **Monitoring & Alerts**

Set up monitoring for:
- RLS policy violations (should be zero)
- Service role usage (should be minimal and logged)
- Failed authentication attempts
- Unusual cross-user data access patterns

---

**🔐 Implementation Priority: CRITICAL**
**⏱️ Estimated Time: 3-4 hours total**
**🎯 Impact: Maximum security with minimal performance overhead**
