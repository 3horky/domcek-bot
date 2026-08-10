.PHONY: bootstrap dev down logs ps migrate backend-check frontend-check check secret-check

bootstrap:
	python3 scripts/bootstrap_local.py

dev: bootstrap
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs --follow

ps:
	docker compose ps

migrate: bootstrap
	docker compose run --rm migrate

backend-check:
	cd backend && uv run ruff format --check .
	cd backend && uv run ruff check .
	cd backend && uv run mypy .
	cd backend && uv run pytest

frontend-check:
	cd frontend && npm run format
	cd frontend && npm run lint
	cd frontend && npm run typecheck
	cd frontend && npm run test
	cd frontend && npm run build

secret-check:
	python3 scripts/check_secrets.py

check: backend-check frontend-check secret-check
