#!/bin/bash
# Quick setup script for local development environment

set -e

echo "🚀 Setting up local development environment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker and Docker Compose are installed${NC}"

# Check if Redis is already running (system service or Docker)
echo -e "${YELLOW}🔍 Checking for existing Redis...${NC}"
if redis-cli ping &> /dev/null; then
    echo -e "${GREEN}✅ Redis already running (system service or Docker)${NC}"
    SKIP_REDIS=true
else
    SKIP_REDIS=false
fi

# Start local infrastructure
if [ "$SKIP_REDIS" = true ]; then
    echo -e "${YELLOW}📦 Starting PostgreSQL container (Redis already running)...${NC}"
    docker-compose -f docker-compose.dev.yml up -d postgres
else
    echo -e "${YELLOW}📦 Starting PostgreSQL and Redis containers...${NC}"
    docker-compose -f docker-compose.dev.yml up -d postgres redis
fi

# Wait for services to be healthy
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 5

# Check PostgreSQL
if docker exec bloggen-postgres-dev psql -U postgres -d bloggen_dev -c "SELECT 1;" &> /dev/null; then
    echo -e "${GREEN}✅ PostgreSQL is ready${NC}"
else
    echo -e "${RED}❌ PostgreSQL failed to start${NC}"
    docker logs bloggen-postgres-dev
    exit 1
fi

# Check Redis (system service or Docker)
if [ "$SKIP_REDIS" = true ]; then
    # Check system Redis
    if redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✅ Redis is ready (system service)${NC}"
    else
        echo -e "${RED}❌ Redis failed to start${NC}"
        exit 1
    fi
else
    # Check Docker Redis
    if docker exec bloggen-redis-dev redis-cli ping &> /dev/null; then
        echo -e "${GREEN}✅ Redis is ready (Docker)${NC}"
    else
        echo -e "${RED}❌ Redis failed to start${NC}"
        docker logs bloggen-redis-dev
        exit 1
    fi
fi

# Setup backend environment
echo -e "${YELLOW}📝 Setting up backend environment...${NC}"
cd backend

if [ ! -f ".env.local" ]; then
    cp .env.development .env.local
    echo -e "${GREEN}✅ Created .env.local from template${NC}"
else
    echo -e "${YELLOW}ℹ️  .env.local already exists${NC}"
fi

cd ..

# Summary
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Local development environment is ready!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}📋 Connection Details:${NC}"
echo "  PostgreSQL: postgresql://postgres:postgres@localhost:5432/bloggen_dev"
echo "  Redis: localhost:6379"
echo "  pgAdmin (optional): http://localhost:5050"
echo ""
echo -e "${YELLOW}🚀 Next Steps:${NC}"
echo "  1. Start Backend:"
echo "     cd backend && source .venv/bin/activate && python src/main.py"
echo ""
echo "  2. Start Frontend (in another terminal):"
echo "     cd frontend-nextjs/blog-generator-ui && npm run dev"
echo ""
echo -e "${YELLOW}🔧 Useful Commands:${NC}"
echo "  View logs:        docker-compose -f docker-compose.dev.yml logs -f"
echo "  Stop services:    docker-compose -f docker-compose.dev.yml down"
echo "  Reset database:   docker-compose -f docker-compose.dev.yml down -v"
echo "  PostgreSQL CLI:   docker exec -it bloggen-postgres-dev psql -U postgres -d bloggen_dev"
echo "  Redis CLI:        docker exec -it bloggen-redis-dev redis-cli"
echo ""
