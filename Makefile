.PHONY: help build up down logs clean dev dev-down dev-logs restart mobile-only mobile-dev

help:
	@echo "Tavern Ordering System - Docker Commands"
	@echo ""
	@echo "Production:"
	@echo "  make build       - Build all Docker images"
	@echo "  make up          - Start all services in production mode"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - View logs from all services"
	@echo "  make restart     - Restart all services"
	@echo ""
	@echo "Development:"
	@echo "  make dev         - Start all services in development mode (hot-reload)"
	@echo "  make dev-down    - Stop development services"
	@echo "  make dev-logs    - View development logs"
	@echo ""
	@echo "Mobile App Only:"
	@echo "  make mobile-only - Start only backend + mobile app (production)"
	@echo "  make mobile-dev  - Start only backend + mobile app (development)"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean       - Remove all containers, images, and volumes"
	@echo ""

# Production commands
build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

# Development commands
dev:
	docker-compose -f docker-compose.dev.yml up

dev-down:
	docker-compose -f docker-compose.dev.yml down

dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f

# Mobile App Only commands
mobile-only:
	docker-compose up -d backend mobile-app

mobile-dev:
	docker-compose -f docker-compose.dev.yml up backend mobile-app

# Cleanup
clean:
	docker-compose down -v --rmi all
	docker-compose -f docker-compose.dev.yml down -v --rmi all

