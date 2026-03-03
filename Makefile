.PHONY: help install dev backend frontend docker clean lint test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies
	cd backend && pip install -e ".[dev]"
	cd frontend && npm install

backend: ## Start backend dev server
	cd backend && uvicorn app.main:app --reload --port 8000

frontend: ## Start frontend dev server
	cd frontend && npm run dev

dev: ## Start both backend and frontend
	$(MAKE) backend &
	$(MAKE) frontend

docker: ## Build and run with Docker
	docker-compose up --build

clean: ## Clean generated files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	rm -rf data/ backend/*.egg-info

lint: ## Run linters
	cd backend && ruff check app/
	cd frontend && npm run lint

test: ## Run tests
	cd backend && pytest tests/
	cd frontend && npm run test

migrate: ## Run database migrations
	cd backend && alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create msg="description")
	cd backend && alembic revision --autogenerate -m "$(msg)"
