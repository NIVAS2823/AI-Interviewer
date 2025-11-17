.PHONY: help up down restart logs logs-backend logs-frontend status clean test shell-backend shell-db install-backend install-frontend

help:
	@echo "AI Interviewer Platform - Development Commands"
	@echo ""
	@echo "Usage: make [command]"
	@echo ""
	@echo "Commands:"
	@echo "  up              Start all services"
	@echo "  down            Stop all services"
	@echo "  restart         Restart all services"
	@echo "  logs            View logs from all services"
	@echo "  logs-backend    View backend logs only"
	@echo "  logs-frontend   View frontend logs only"
	@echo "  status          Check service status"
	@echo "  clean           Remove all containers and volumes"
	@echo "  test            Run all tests"
	@echo "  test-backend    Run backend tests"
	@echo "  test-frontend   Run frontend tests"
	@echo "  shell-backend   Enter backend container shell"
	@echo "  shell-db        Enter MongoDB shell"
	@echo "  install-backend Install backend dependencies"
	@echo "  install-frontend Install frontend dependencies"

up:
	docker-compose up -d
	@echo "✅ All services started"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

down:
	docker-compose down
	@echo "✅ All services stopped"

restart:
	docker-compose restart
	@echo "✅ All services restarted"

logs:
	docker-compose logs -f

logs-backend:
	docker-compose logs -f backend

logs-frontend:
	docker-compose logs -f frontend

status:
	docker-compose ps

clean:
	docker-compose down -v
	@echo "✅ All containers and volumes removed"

test:
	@echo "Running backend tests..."
	docker-compose exec backend pytest
	@echo "Running frontend tests..."
	docker-compose exec frontend npm test

test-backend:
	docker-compose exec backend pytest -v

test-frontend:
	docker-compose exec frontend npm test

shell-backend:
	docker-compose exec backend /bin/bash

shell-db:
	docker-compose exec mongodb mongosh ai_interviewer

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

build:
	docker-compose build

rebuild:
	docker-compose build --no-cache