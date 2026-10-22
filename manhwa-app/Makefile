.PHONY: install run test lint docker
install:
	python -m venv .venv && . .venv/bin/activate && pip install -r backend/requirements-dev.txt
run:
	cd backend && uvicorn app.main:app --reload
test:
	cd backend && pytest -q
lint:
	cd backend && ruff check .
docker:
	docker compose up --build
