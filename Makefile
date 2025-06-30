# Makefile for running tests with Docker Compose

# Variables
SERVICE_NAME=test
DOCKER_COMPOSE=docker-compose -f docker-compose.yml -f docker-compose.test.yml

.PHONY: test test-unit test-integration test-cov test-lint test-all clean help

# Run all tests (unit + integration)
test: build
	@echo "Running all tests..."
	$(DOCKER_COMPOSE) run --rm $(SERVICE_NAME) pytest tests/

# Run unit tests only
test-unit: build
	@echo "Running unit tests..."
	$(DOCKER_COMPOSE) run --rm $(SERVICE_NAME) pytest tests/unit/

# Run integration tests only
test-integration: build
	@echo "Running integration tests..."
	$(DOCKER_COMPOSE) run --rm $(SERVICE_NAME) pytest tests/integration/

# Run tests with coverage report
test-cov: build
	@echo "Running tests with coverage..."
	$(DOCKER_COMPOSE) run --rm $(SERVICE_NAME) pytest --cov=app --cov-report=term-missing --cov-report=html tests/

# Run linting
test-lint: build
	@echo "Running linting..."
	$(DOCKER_COMPOSE) run --rm $(SERVICE_NAME) black --check .
	$(DOCKER_COMPOSE) run --rm $(SERVICE_NAME) isort --check-only .
	$(DOCKER_COMPOSE) run --rm $(SERVICE_NAME) flake8 .

# Run all tests and linting
test-all: test test-lint

# Build the test container
build:
	$(DOCKER_COMPOSE) build $(SERVICE_NAME)

# Clean up containers and volumes
clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -delete
	find ../. -name '.coverage' -delete

format:
	black . --line-length 79
	isort .

test-coverage:
	pytest tests/unit/ --cov --cov-report=term-missing --cov-report=html

# Show help
help:
	@echo "\nAvailable commands:"
	@echo "  make help              - Show this help message"
	@echo "  make test              - Run all tests"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests only"
	@echo "  make test-coverage     - Run unit tests with coverage report"
	@echo "  make format            - Format code using black and isort"
	@echo "  make clean             - Remove Python cache and coverage files"
	@echo "  make run               - Run the application"
	@echo "  make docker-build      - Build Docker image"
	@echo "  make docker-run        - Run the application in Docker"
	@echo "  make docker-test       - Run tests in Docker"
	@echo "  make docker-clean      - Remove Docker containers and images"
	@echo "  make install           - Install dependencies"
	@echo "  make install-dev       - Install development dependencies"
	@echo "  make lint              - Run linters (black, isort, flake8)"
	@echo "  make check-formatting  - Check code formatting without making changes"
	@echo "  test-lint    - Run linting checks"
	@echo "  test-all     - Run all tests and linting"
	@echo "  build        - Build the test container"
	@echo "  clean        - Clean up containers and volumes"
	@echo "  help         - Show this help message"
