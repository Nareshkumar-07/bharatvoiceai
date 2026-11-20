.PHONY: help install backend frontend test build docker migrate seed clean

help:
	@echo "BharatVoice AI"
	@echo "  make install   install backend + frontend dependencies"
	@echo "  make backend   run the API on :8000"
	@echo "  make frontend  run the UI on :5173"
	@echo "  make test      run backend tests"
	@echo "  make build     type-check and build the frontend"
	@echo "  make migrate   apply database migrations"
	@echo "  make docker    build and start the full stack"

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

backend:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	cd backend && python -m pytest -q

build:
	cd frontend && npm run build

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m app.database.init_db

docker:
	docker compose up --build

clean:
	rm -rf frontend/dist backend/__pycache__ backend/.pytest_cache
