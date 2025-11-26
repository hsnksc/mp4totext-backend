# ============================================================================
# MP4toText Backend - Makefile
# ============================================================================
# Quick commands for Docker operations
# ============================================================================

.PHONY: help build up down restart logs ps clean test

# Default target
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)MP4toText Backend - Docker Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ============================================================================
# Production Commands
# ============================================================================

build: ## Build production Docker images
	@echo "$(BLUE)Building production images...$(NC)"
	docker-compose build

up: ## Start production containers
	@echo "$(GREEN)Starting production containers...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✅ Containers started!$(NC)"
	@echo "$(YELLOW)API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)Docs: http://localhost:8000/docs$(NC)"

down: ## Stop and remove production containers
	@echo "$(RED)Stopping production containers...$(NC)"
	docker-compose down

restart: ## Restart production containers
	@echo "$(YELLOW)Restarting production containers...$(NC)"
	docker-compose restart

logs: ## Show production logs
	docker-compose logs -f

ps: ## Show running containers
	docker-compose ps

# ============================================================================
# Development Commands
# ============================================================================

dev-build: ## Build development Docker images
	@echo "$(BLUE)Building development images...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml build

dev-up: ## Start development containers with hot reload
	@echo "$(GREEN)Starting development containers...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "$(GREEN)✅ Development containers started!$(NC)"
	@echo "$(YELLOW)API: http://localhost:8000$(NC)"
	@echo "$(YELLOW)Docs: http://localhost:8000/docs$(NC)"
	@echo "$(YELLOW)Flower: http://localhost:5555 (admin:admin123)$(NC)"
	@echo "$(YELLOW)pgAdmin: http://localhost:5050 (admin@mp4totext.local:admin123)$(NC)"
	@echo "$(YELLOW)Redis Commander: http://localhost:8081$(NC)"
	@echo "$(YELLOW)MinIO Console: http://localhost:9001$(NC)"

dev-down: ## Stop development containers
	@echo "$(RED)Stopping development containers...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

dev-restart: ## Restart development containers
	@echo "$(YELLOW)Restarting development containers...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart

dev-logs: ## Show development logs
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# ============================================================================
# Database Commands
# ============================================================================

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running migrations...$(NC)"
	docker-compose exec backend alembic upgrade head

db-rollback: ## Rollback last migration
	@echo "$(YELLOW)Rolling back migration...$(NC)"
	docker-compose exec backend alembic downgrade -1

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U postgres -d mp4totext

db-backup: ## Backup database
	@echo "$(BLUE)Creating database backup...$(NC)"
	docker-compose exec postgres pg_dump -U postgres mp4totext > backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Backup created!$(NC)"

# ============================================================================
# Testing Commands
# ============================================================================

test: ## Run tests in container
	@echo "$(BLUE)Running tests...$(NC)"
	docker-compose exec backend pytest tests/ -v --cov=app --cov-report=html

test-unit: ## Run unit tests only
	docker-compose exec backend pytest tests/ -v -m unit

test-integration: ## Run integration tests only
	docker-compose exec backend pytest tests/ -v -m integration

coverage: ## Generate coverage report
	docker-compose exec backend pytest tests/ --cov=app --cov-report=html --cov-report=term
	@echo "$(GREEN)✅ Coverage report: htmlcov/index.html$(NC)"

# ============================================================================
# Utility Commands
# ============================================================================

shell: ## Open backend container shell
	docker-compose exec backend bash

redis-cli: ## Open Redis CLI
	docker-compose exec redis redis-cli -a $${REDIS_PASSWORD:-redis123}

minio-shell: ## Open MinIO shell
	docker-compose exec minio sh

clean: ## Remove containers, volumes, and images
	@echo "$(RED)⚠️  This will remove all containers, volumes, and images!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v --rmi all; \
		echo "$(GREEN)✅ Cleaned up!$(NC)"; \
	fi

clean-volumes: ## Remove all volumes (data will be lost!)
	@echo "$(RED)⚠️  This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		echo "$(GREEN)✅ Volumes removed!$(NC)"; \
	fi

health: ## Check container health status
	@echo "$(BLUE)Checking container health...$(NC)"
	@docker-compose ps | grep -E "(healthy|unhealthy|starting)" || echo "No health checks configured"

stats: ## Show container resource usage
	docker stats $$(docker-compose ps -q)

prune: ## Remove unused Docker resources
	@echo "$(YELLOW)Pruning unused Docker resources...$(NC)"
	docker system prune -f
	@echo "$(GREEN)✅ Cleanup completed!$(NC)"

# ============================================================================
# Monitoring Commands
# ============================================================================

flower: ## Open Flower (Celery monitoring)
	@open http://localhost:5555 || xdg-open http://localhost:5555 || start http://localhost:5555

pgadmin: ## Open pgAdmin
	@open http://localhost:5050 || xdg-open http://localhost:5050 || start http://localhost:5050

redis-ui: ## Open Redis Commander
	@open http://localhost:8081 || xdg-open http://localhost:8081 || start http://localhost:8081

minio-ui: ## Open MinIO Console
	@open http://localhost:9001 || xdg-open http://localhost:9001 || start http://localhost:9001

docs: ## Open API documentation
	@open http://localhost:8000/docs || xdg-open http://localhost:8000/docs || start http://localhost:8000/docs

# ============================================================================
# Quick Start
# ============================================================================

quickstart: ## Quick start for development
	@echo "$(GREEN)🚀 Quick starting MP4toText Backend...$(NC)"
	@$(MAKE) dev-build
	@$(MAKE) dev-up
	@echo ""
	@echo "$(GREEN)✅ All done! Your services are running:$(NC)"
	@echo ""
	@$(MAKE) dev-urls

dev-urls: ## Show all development URLs
	@echo "$(BLUE)📝 Development URLs:$(NC)"
	@echo "  $(YELLOW)API:$(NC)              http://localhost:8000"
	@echo "  $(YELLOW)API Docs:$(NC)         http://localhost:8000/docs"
	@echo "  $(YELLOW)Health Check:$(NC)     http://localhost:8000/health"
	@echo "  $(YELLOW)Flower:$(NC)           http://localhost:5555 (admin:admin123)"
	@echo "  $(YELLOW)pgAdmin:$(NC)          http://localhost:5050 (admin@mp4totext.local:admin123)"
	@echo "  $(YELLOW)Redis Commander:$(NC)  http://localhost:8081"
	@echo "  $(YELLOW)MinIO Console:$(NC)    http://localhost:9001 (dev_minio:dev_minio_123)"
