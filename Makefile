# Makefile for Enhanced MCP Test Environment

.PHONY: helrun-server:
	python3 -m server_side.server

run-enhanced-server:
	python3 -m server_side.enhanced_server

run-client:
	python3 -m client_side.client

run-docker-compose:
	docker-compose up -d

stop-docker-compose:
	docker-compose down -v

# Development and Testing targets
setup-dev:
	@echo "Setting up development environment..."
	python3 -m venv venv
	@echo "Activate virtual environment with: source venv/bin/activate"
	@echo "Then run: make install-deps"

install-deps:
	pip install --upgrade pip
	pip install -r requirements.txt

test:
	python tests/run_tests.py --suite integration

test-unit:
	pytest tests/test_tools_functions.py -v

test-integration:
	python tests/run_tests.py --suite integration --mock

test-performance:
	python tests/run_tests.py --suite performance --mock

test-stress:
	python tests/run_tests.py --suite stress --mock

test-all:
	python tests/run_tests.py --suite all --mock

# Code quality targets
lint:
	flake8 . --count --max-line-length=100 --statistics
	mypy --ignore-missing-imports .

format:
	black .
	isort .

security-scan:
	safety check
	bandit -r . -f json -o security-report.json

# Cleanup targets
clean:
	docker rmi mcp_agent mcp_server mcp_client 2>/dev/null || true
	docker system prune -f

clean-all: clean
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf test_reports/
	rm -rf *.log
	rm -f security-report.jsonagent build-server build-client run-agent run-server run-client run-docker-compose stop-docker-compose clean
.PHONY: test test-unit test-integration test-performance test-stress test-all lint format setup-dev install-deps

help:
	@echo "Available targets:"
	@echo "  build                Build all Docker images"
	@echo "  build-agent          Build agent Docker image"
	@echo "  build-server         Build server Docker image"
	@echo "  build-client         Build client Docker image"
	@echo "  run-agent            Run agent locally (requires dependencies)"
	@echo "  run-server           Run server locally (requires dependencies)"
	@echo "  run-enhanced-server  Run enhanced server with monitoring"
	@echo "  run-client           Run client locally (requires dependencies)"
	@echo "  run-docker-compose   Start all services with docker-compose"
	@echo "  stop-docker-compose  Stop all services with docker-compose"
	@echo "  clean                Remove Docker images"
	@echo ""
	@echo "Development and Testing:"
	@echo "  setup-dev            Setup development environment"
	@echo "  install-deps         Install Python dependencies"
	@echo "  test                 Run all tests"
	@echo "  test-unit            Run unit tests"
	@echo "  test-integration     Run integration tests"
	@echo "  test-performance     Run performance tests"
	@echo "  test-stress          Run stress tests"
	@echo "  test-all             Run comprehensive test suite"
	@echo "  lint                 Run code linting"
	@echo "  format               Format code with black and isort"
	@echo "  security-scan        Run security scans"

# Build targets
build: build-agent build-server build-client

build-agent:
	docker build -t mcp_agent ./agent

build-server:
	docker build -t mcp_server ./server_side

build-client:
	docker build -t mcp_client ./client_side

# Run targets
run-agent:
	python3 -m agent.agent

run-server:
	python3 -m server_side.server

run-enhanced-server:
	python3 -m server_side.enhanced_server

run-client:
	python3 -m client_side.client

run-server:
	python3 -m server_side.server

run-client:
	python3 -m client_side.client

run-docker-compose:
	docker-compose up --build

stop-docker-compose:
	docker-compose down

clean:
	docker rmi mcp_agent mcp_server mcp_client || true

clean-compose:
	docker-compose down -v --rmi all --remove-orphans