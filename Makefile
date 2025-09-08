# Makefile for MCP Test Environment

.PHONY: help build build-agent build-server build-client run-agent run-server run-client run-docker-compose stop-docker-compose clean

help:
	@echo "Available targets:"
	@echo "  build                Build all Docker images"
	@echo "  build-agent          Build agent Docker image"
	@echo "  build-server         Build server Docker image"
	@echo "  build-client         Build client Docker image"
	@echo "  run-agent            Run agent locally (requires dependencies)"
	@echo "  run-server           Run server locally (requires dependencies)"
	@echo "  run-client           Run client locally (requires dependencies)"
	@echo "  run-docker-compose   Start all services with docker-compose"
	@echo "  stop-docker-compose  Stop all services with docker-compose"
	@echo "  clean                Remove Docker images"

build: build-agent build-server build-client

build-agent:
	docker build -t mcp_agent ./agent

build-server:
	docker build -t mcp_server ./server_side

build-client:
	docker build -t mcp_client ./client_side

run-agent:
	python3 -m agent.agent

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
