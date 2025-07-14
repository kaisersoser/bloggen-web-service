# Blog Generator - Development and Deployment Commands

.PHONY: help install dev test clean build deploy

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies for both backend and frontend
	@echo "Installing backend dependencies..."
	cd backend && python -m pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

dev-backend:  ## Start backend development server
	cd backend && python src/main.py

dev-frontend:  ## Start frontend development server
	cd frontend && npm run dev

dev:  ## Start both backend and frontend in development mode
	@echo "Starting development servers..."
	make dev-backend &
	make dev-frontend

test:  ## Run all tests
	cd backend && python -m pytest tests/ -v

test-backend:  ## Run backend tests only
	cd backend && python -m pytest tests/ -v

lint:  ## Run linting and code formatting
	cd backend && black src/ && flake8 src/
	cd frontend && npm run lint

clean:  ## Clean build artifacts and cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	cd frontend && rm -rf .next node_modules/.cache

build:  ## Build for production
	cd frontend && npm run build

docker-build:  ## Build Docker containers
	docker-compose build

docker-up:  ## Start Docker containers
	docker-compose up -d

docker-down:  ## Stop Docker containers
	docker-compose down

backup-db:  ## Backup database
	@echo "Creating database backup..."
	cp backend/src/bloggen/db/chroma.sqlite3 "backup_$(shell date +%Y%m%d_%H%M%S).sqlite3"

setup:  ## Initial project setup
	@echo "Setting up project..."
	chmod +x scripts/setup.sh
	./scripts/setup.sh

deploy:  ## Deploy to production
	@echo "Deploying to production..."
	chmod +x scripts/deploy.sh
	./scripts/deploy.sh
