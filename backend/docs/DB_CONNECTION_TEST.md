# Database Connection Test Scripts

Quick diagnostic tools to test your DATABASE_URL connection string without exposing credentials.

## 📁 Files

- `test_db_connection.py` - Python script that tests database connectivity
- `test_db_connection.sh` - Bash wrapper that loads .env and runs the test

## 🚀 Usage

### Method 1: Using the Shell Script (Recommended)

```bash
cd backend
./test_db_connection.sh
```

This will:
1. Load DATABASE_URL from your `.env` file
2. Activate virtual environment if available
3. Run the connection test
4. Show detailed results

### Method 2: Manual Python Script

```bash
cd backend
source .venv/bin/activate  # Activate venv
export DATABASE_URL="your_connection_string_here"
python test_db_connection.py
```

### Method 3: Test Specific URL Without .env

```bash
cd backend
source .venv/bin/activate
DATABASE_URL="postgresql://user:pass@host:port/db" python test_db_connection.py
```

## 🔍 What It Tests

1. **URL Parsing** - Validates the connection string format
2. **Network Connectivity** - Tests if host is reachable
3. **Authentication** - Verifies username/password
4. **Database Access** - Confirms database exists and is accessible
5. **Query Execution** - Runs a simple query to test functionality
6. **Table Discovery** - Lists tables to confirm proper access

## ✅ Success Output

```
🔍 Testing database connection...
   Scheme: postgresql
   Host: aws-0-eu-west-3.pooler.supabase.com
   Port: 6543
   Database: /postgres
   Username: postgres.agaejevkyzufcqptatdw
   Password: **************

🔌 Attempting to connect...
✅ Connection pool created successfully!
🧪 Testing simple query...
✅ Query executed successfully!
   PostgreSQL version: PostgreSQL 15.1 on x86_64-pc-linux-gnu...

📊 Found 5 tables in database:
   - users
   - sessions
   - blogs
   - accounts
   - verification_tokens

✅ SUCCESS: Database connection is working correctly!
```

## ❌ Common Errors and Solutions

### Error: "AUTHENTICATION FAILED: Invalid password"

**Possible causes:**
- Double colon `::` instead of single colon `:` in URL
- Special characters in password not URL-encoded
- Incorrect password

**Solution:**
```bash
# Check your DATABASE_URL format
# Should be: postgresql://user:password@host:port/db
# NOT:       postgresql://user::password@host:port/db

# URL encode special characters:
# ! = %21
# @ = %40
# # = %23
# $ = %24
# % = %25
```

### Error: "NETWORK ERROR: [Errno 101] Network is unreachable"

**Possible causes:**
- Incorrect hostname
- Supabase project paused/deleted
- Firewall blocking connection
- DNS resolution failure

**Solution:**
- Verify hostname in Supabase Dashboard
- Check Supabase project status
- Try pinging the host: `ping aws-0-eu-west-3.pooler.supabase.com`

### Error: "TIMEOUT: Connection attempt timed out"

**Possible causes:**
- Network connectivity issues
- Firewall blocking outbound connections
- Incorrect port (should be 6543 for pooling)

**Solution:**
- Check your internet connection
- Verify port is 6543 (pooler) not 5432 (direct)
- Check firewall rules

### Error: "DATABASE NOT FOUND: Invalid database name"

**Solution:**
- Check the database name in your URL (usually `/postgres`)
- Verify in Supabase Dashboard

## 🔒 Security Notes

- ✅ Passwords are masked in output
- ✅ No credentials written to logs or files
- ✅ Script reads from environment variables only
- ✅ Safe to run in any environment

## 🐛 Debugging Tips

1. **Test locally first** - If local test fails, Railway will fail too
2. **Check .env file** - Ensure DATABASE_URL is on a single line
3. **No quotes needed** - Use `DATABASE_URL=postgresql://...` not `DATABASE_URL="postgresql://..."`
4. **Watch for line breaks** - Long URLs can wrap in editors
5. **Copy from Supabase** - Get connection string directly from Supabase Dashboard → Database → Connection Pooling

## 📚 Related Documentation

- `docs/RAILWAY_ENV_VARIABLES.md` - Environment variable reference
- `docs/DEPLOYMENT_GUIDE.md` - Full deployment guide
- `docs/DEPLOYMENT_CONTEXT_SNAPSHOT.md` - Current deployment status
