"""
Configuration management for MCP Test Environment
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class DatabaseConfig:
    """Database configuration"""

    host: str = "localhost"
    port: int = 5432
    name: str = "mcp_test"
    user: str = "mcp_user"
    password: str = "mcp_pass"
    sqlite_path: str = "./data/sample.db"


@dataclass
class ServerConfig:
    """Server configuration"""

    host: str = "localhost"
    port: int = 8000
    debug: bool = True
    workers: int = 1
    timeout: int = 30
    max_connections: int = 100


@dataclass
class AgentConfig:
    """Agent configuration"""

    max_iterations: int = 10
    timeout: int = 60
    retry_attempts: int = 3
    retry_delay: float = 1.0
    bedrock_model: str = "anthropic.claude-3-haiku-20240307-v1:0"
    bedrock_region: str = "us-east-1"


@dataclass
class ClientConfig:
    """Client configuration"""

    server_url: str = "http://localhost:8000"
    timeout: int = 30
    max_retries: int = 3
    gradio_port: int = 7860


@dataclass
class TestConfig:
    """Test configuration"""

    test_data_path: str = "./tests/data"
    mock_responses: bool = False
    parallel_tests: bool = True
    test_timeout: int = 300
    performance_tests: bool = False


@dataclass
class LoggingConfig:
    """Logging configuration"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class MCPConfig:
    """Main MCP configuration"""

    environment: str = "development"
    database: DatabaseConfig = DatabaseConfig()
    server: ServerConfig = ServerConfig()
    agent: AgentConfig = AgentConfig()
    client: ClientConfig = ClientConfig()
    test: TestConfig = TestConfig()
    logging: LoggingConfig = LoggingConfig()


def load_config() -> MCPConfig:
    """Load configuration from environment variables and defaults"""

    # Environment
    env = os.getenv("MCP_ENVIRONMENT", "development")

    # Database config
    db_config = DatabaseConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        name=os.getenv("DB_NAME", "mcp_test"),
        user=os.getenv("DB_USER", "mcp_user"),
        password=os.getenv("DB_PASSWORD", "mcp_pass"),
        sqlite_path=os.getenv("SQLITE_PATH", "./data/sample.db"),
    )

    # Server config
    server_config = ServerConfig(
        host=os.getenv("SERVER_HOST", "localhost"),
        port=int(os.getenv("SERVER_PORT", "8000")),
        debug=os.getenv("SERVER_DEBUG", "true").lower() == "true",
        workers=int(os.getenv("SERVER_WORKERS", "1")),
        timeout=int(os.getenv("SERVER_TIMEOUT", "30")),
        max_connections=int(os.getenv("SERVER_MAX_CONNECTIONS", "100")),
    )

    # Agent config
    agent_config = AgentConfig(
        max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "10")),
        timeout=int(os.getenv("AGENT_TIMEOUT", "60")),
        retry_attempts=int(os.getenv("AGENT_RETRY_ATTEMPTS", "3")),
        retry_delay=float(os.getenv("AGENT_RETRY_DELAY", "1.0")),
        bedrock_model=os.getenv(
            "BEDROCK_MODEL", "anthropic.claude-3-haiku-20240307-v1:0"
        ),
        bedrock_region=os.getenv("BEDROCK_REGION", "us-east-1"),
    )

    # Client config
    client_config = ClientConfig(
        server_url=os.getenv("CLIENT_SERVER_URL", "http://localhost:8000"),
        timeout=int(os.getenv("CLIENT_TIMEOUT", "30")),
        max_retries=int(os.getenv("CLIENT_MAX_RETRIES", "3")),
        gradio_port=int(os.getenv("GRADIO_PORT", "7860")),
    )

    # Test config
    test_config = TestConfig(
        test_data_path=os.getenv("TEST_DATA_PATH", "./tests/data"),
        mock_responses=os.getenv("MOCK_RESPONSES", "false").lower() == "true",
        parallel_tests=os.getenv("PARALLEL_TESTS", "true").lower() == "true",
        test_timeout=int(os.getenv("TEST_TIMEOUT", "300")),
        performance_tests=os.getenv("PERFORMANCE_TESTS", "false").lower() == "true",
    )

    # Logging config
    logging_config = LoggingConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format=os.getenv(
            "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ),
        file_path=os.getenv("LOG_FILE_PATH"),
        max_file_size=int(os.getenv("LOG_MAX_FILE_SIZE", str(10 * 1024 * 1024))),
        backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
    )

    return MCPConfig(
        environment=env,
        database=db_config,
        server=server_config,
        agent=agent_config,
        client=client_config,
        test=test_config,
        logging=logging_config,
    )


# Global config instance
config = load_config()
