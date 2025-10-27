.PHONY: help build up down restart logs status clean prod-up prod-down prod-restart prod-logs deploy-remote

# Default target
help:
	@echo "📚 The Library - Docker Commands"
	@echo ""
	@echo "Development:"
	@echo "  make build          Build development containers"
	@echo "  make up             Start development services"
	@echo "  make down           Stop development services"
	@echo "  make restart        Restart development services"
	@echo "  make logs           View development logs"
	@echo "  make status         Check service status"
	@echo "  make clean          Clean restart (rebuild + up)"
	@echo ""
	@echo "Production:"
	@echo "  make prod-up        Start production services"
	@echo "  make prod-down      Stop production services"
	@echo "  make prod-restart   Restart production services"
	@echo "  make prod-logs      View production logs"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-remote SSH_HOST=retcon   Deploy to remote server"
	@echo ""

# Development commands
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart: down up

logs:
	docker compose logs -f

status:
	docker compose ps

clean: down
	docker compose build --no-cache
	docker compose up -d

# Production commands (use prod file only - base file has naming conflicts)
prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-restart: prod-down prod-up

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

# Remote deployment
deploy-remote:
	@if [ -z "$(SSH_HOST)" ]; then \
		echo "❌ Error: SSH_HOST not set"; \
		echo "Usage: make deploy-remote SSH_HOST=retcon"; \
		exit 1; \
	fi
	@echo "🚀 Deploying the-library to $(SSH_HOST)..."
	@echo "📥 Pulling latest code and restarting services..."
	ssh $(SSH_HOST) "cd /opt/the-library && git pull && make prod-restart"
	@echo "✅ Deployment complete!"
	@echo "   Check: https://thelibrary.retconblackmountain.info"
