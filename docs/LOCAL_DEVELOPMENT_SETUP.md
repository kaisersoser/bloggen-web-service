# Development Environment Setup Guide

## 🎯 Best Practice: Hybrid Database Architecture

This project follows industry best practices by separating development, staging, and production environments:

- **Development**: Local PostgreSQL Docker (fast, isolated, free)
- **Staging**: Supabase staging project (optional, for pre-prod testing)
- **Production**: Supabase production (managed, scalable, reliable)

## 📋 Quick Start - Local Development

### 1. Start Local Infrastructure
```bash
# Start PostgreSQL + Redis in Docker
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose -f docker-compose.dev.yml ps

# Check PostgreSQL health
docker exec bloggen-postgres-dev psql -U postgres -d bloggen_dev -c "SELECT version();"

# Check Redis health
docker exec bloggen-redis-dev redis-cli ping
```

### 2. Configure Backend for Local Database
```bash
# Copy development environment template
cd backend
cp .env.development .env.local

# Edit .env.local if needed (default values should work)
# DATABASE_URL="postgresql://postgres:postgres@localhost:5432/bloggen_dev"
```

### 3. Start Backend
```bash
cd backend
source .venv/bin/activate
python src/main.py
```

Expected output:
```
✅ Redis connection established
✅ Database pool created with 10 connections
✅ TaskManager cache warmup restored 0 tasks from database
INFO:     Uvicorn running on https://0.0.0.0:8000
```

### 4. Start Frontend
```bash
cd frontend-nextjs/blog-generator-ui
npm run dev
```

## 🗄️ Database Management

### View Database with pgAdmin (Optional)
```bash
# Start pgAdmin alongside other services
docker-compose -f docker-compose.dev.yml --profile tools up -d

# Access pgAdmin at: http://localhost:5050
# Email: admin@bloggen.local
# Password: admin

# Add connection:
# - Host: postgres (or host.docker.internal)
# - Port: 5432
# - Database: bloggen_dev
# - Username: postgres
# - Password: postgres
```

### Direct PostgreSQL Access
```bash
# Connect via psql
docker exec -it bloggen-postgres-dev psql -U postgres -d bloggen_dev

# List tables
\dt

# View users
SELECT id, email, role FROM users;

# View tasks
SELECT id, user_id, topic, status FROM task_status;

# Exit
\q
```

### View Logs
```bash
# PostgreSQL logs
docker logs -f bloggen-postgres-dev

# Redis logs
docker logs -f bloggen-redis-dev

# All services
docker-compose -f docker-compose.dev.yml logs -f
```

## 🔄 Environment Switching

### Switch to Local Development (Default)
```bash
cd backend
ln -sf .env.development .env.local
# Edit main .env or use .env.local
```

### Switch to Supabase Staging (if available)
```bash
cd backend
cp .env .env.backup
# Update DATABASE_URL to staging Supabase URL
```

### Switch to Supabase Production (Dangerous!)
```bash
# ⚠️ Only for production deployments
cd backend
# Use production DATABASE_URL
```

## 🧪 Testing with Local Database

### Run Unit Tests
```bash
cd backend
source .venv/bin/activate

# Run all tests with local database
pytest src/tests/ -v

# Run specific test suite
pytest src/tests/test_sse_handler.py -v

# Run with coverage
pytest src/tests/ --cov=src --cov-report=html
```

### Reset Development Database
```bash
# Stop and remove container + volume
docker-compose -f docker-compose.dev.yml down -v

# Start fresh (init.sql will run again)
docker-compose -f docker-compose.dev.yml up -d
```

## 📊 Benefits of This Architecture

### ✅ Development (Local PostgreSQL)
- **Fast**: No network latency
- **Isolated**: Your changes don't affect others
- **Free**: No cloud costs
- **Safe**: Can reset/break without consequences
- **Offline**: Works without internet

### ✅ Staging (Supabase Staging - Optional)
- **Pre-Production**: Test deployments before prod
- **Migration Testing**: Verify schema changes safely
- **Integration Testing**: Test with production-like setup
- **Team Collaboration**: Shared testing environment

### ✅ Production (Supabase Production)
- **Managed**: Auto-scaling, backups, monitoring
- **Reliable**: 99.9% uptime SLA
- **Secure**: Built-in security features
- **Performance**: Optimized for production workloads
- **Observability**: Real-time metrics and logs

## 🚀 CI/CD Pipeline Benefits

With local Docker databases, you can run:
```yaml
# .github/workflows/test.yml
- name: Start test database
  run: docker-compose -f docker-compose.dev.yml up -d

- name: Run tests
  run: pytest src/tests/ --parallel

- name: Cleanup
  run: docker-compose -f docker-compose.dev.yml down -v
```

**Parallel tests are now possible** without conflicting with production!

## 🔧 Troubleshooting

### Port Already in Use
```bash
# Check what's using port 5432
lsof -i :5432

# Stop existing PostgreSQL
sudo systemctl stop postgresql
# OR
docker stop $(docker ps -q --filter "expose=5432")
```

### Cannot Connect to Database
```bash
# Verify container is running
docker ps --filter "name=bloggen-postgres-dev"

# Check logs
docker logs bloggen-postgres-dev

# Restart services
docker-compose -f docker-compose.dev.yml restart
```

### Database Not Initialized
```bash
# Remove volume and restart
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d

# Watch initialization
docker logs -f bloggen-postgres-dev
```

## 📚 Additional Resources

- [PostgreSQL Docker Official Image](https://hub.docker.com/_/postgres)
- [Redis Docker Official Image](https://hub.docker.com/_/redis)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Supabase Documentation](https://supabase.com/docs)

## 🎯 Next Steps

1. ✅ Start local development environment
2. ✅ Run backend and frontend
3. ✅ Run E2E tests with local database
4. ✅ Develop features without affecting production
5. 📝 When ready for deployment, switch to production Supabase URL
