.PHONY: dev test migrate seed install

dev:
	uvicorn src.api.main:app --reload --port 8000

test:
	python -m pytest tests/ -v

migrate:
	alembic upgrade head

seed:
	python -m scripts.seed

install:
	pip install -e .
