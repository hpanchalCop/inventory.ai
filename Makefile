.PHONY: help install start stop restart logs test clean init-db sample-data docker-build docker-push

help:
	@echo "inventory.ai - Makefile commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make install        - Install Python dependencies"
	@echo "  make start          - Start services with docker-compose"
	@echo "  make stop           - Stop services"
	@echo "  make restart        - Restart services"
	@echo "  make logs           - View service logs"
	@echo "  make test           - Run tests"
	@echo "  make init-db        - Initialize database"
	@echo "  make sample-data    - Populate database with sample data"
	@echo "  make docker-build   - Build Docker images"
	@echo "  make clean          - Clean up temporary files"

install:
	pip install -r requirements.txt

start:
	docker-compose up -d
	@echo "Services started. Access them at:"
	@echo "  API: http://localhost:8000"
	@echo "  Dashboard: http://localhost:8050"

stop:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

test:
	pytest tests/ -v

init-db:
	python init_db.py

sample-data:
	python populate_sample_data.py

docker-build:
	docker build -f Dockerfile.api -t inventory-ai-api:latest .
	docker build -f Dockerfile.dashboard -t inventory-ai-dashboard:latest .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf .pytest_cache
	rm -f test.db
