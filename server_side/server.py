"""
Enhanced MCP Server with monitoring and testing capabilities
"""

import logging
import sqlite3
import json
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from contextlib import asynccontextmanager

from fastmcp import FastMCP
from utils.input_models import (
    FileOperationInput,
    DatabaseQueryInput,
    APICallInput,
)
from utils.tools_functions import (
    _filesystem_operation,
    _execute_database_query,
    _api_call,
)

# Enhanced imports
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import load_config
from utils.logging import setup_logging, get_logger
from utils.metrics import get_metrics_collector, time_operation, record_metric

# Load configuration
config = load_config()
setup_logging(config.logging)
logger = get_logger(__name__)
metrics = get_metrics_collector()


class EnhancedMCPServer:
    """Enhanced FastMCP Server with monitoring and testing capabilities"""

    def __init__(self, data_path: str = "./data"):
        self.config = config
        self.data_path = Path(data_path)
        self.data_path.mkdir(exist_ok=True)

        # Initialize metrics
        self.metrics = metrics

        # Create FastMCP app
        self.app = FastMCP("Enhanced AI Agent MCP Server")

        # Initialize components
        self._init_sample_database()
        self._register_tools()
        self._register_health_endpoints()

        logger.info("Enhanced MCP Server initialized")

    def _init_sample_database(self):
        """Initialize Sample Database with comprehensive test data"""
        db_path = self.data_path / "sample.db"

        try:
            with time_operation("database_init"):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Create enhanced tables
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        first_name TEXT,
                        last_name TEXT,
                        age INTEGER,
                        active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS products (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        price DECIMAL(10, 2) NOT NULL,
                        category TEXT NOT NULL,
                        in_stock BOOLEAN DEFAULT TRUE,
                        quantity INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER,
                        product_id INTEGER,
                        quantity INTEGER NOT NULL,
                        unit_price DECIMAL(10, 2),
                        total_price DECIMAL(10, 2),
                        status TEXT DEFAULT 'pending',
                        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (product_id) REFERENCES products (id)
                    )
                """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        description TEXT,
                        parent_id INTEGER,
                        FOREIGN KEY (parent_id) REFERENCES categories (id)
                    )
                """
                )

                # Insert comprehensive test data
                users_data = [
                    ("alice_j", "alice@example.com", "Alice", "Johnson", 28, True),
                    ("bob_smith", "bob@example.com", "Bob", "Smith", 34, True),
                    ("charlie_b", "charlie@example.com", "Charlie", "Brown", 22, True),
                    ("diana_w", "diana@example.com", "Diana", "Wilson", 45, False),
                    ("eve_davis", "eve@example.com", "Eve", "Davis", 31, True),
                ]
                cursor.executemany(
                    "INSERT OR IGNORE INTO users (username, email, first_name, last_name, age, active) VALUES (?, ?, ?, ?, ?, ?)",
                    users_data,
                )

                categories_data = [
                    ("Electronics", "Electronic devices and accessories", None),
                    ("Computers", "Desktop and laptop computers", 1),
                    ("Mobile", "Mobile phones and tablets", 1),
                    ("Furniture", "Home and office furniture", None),
                    ("Books", "Physical and digital books", None),
                ]
                cursor.executemany(
                    "INSERT OR IGNORE INTO categories (name, description, parent_id) VALUES (?, ?, ?)",
                    categories_data,
                )

                products_data = [
                    (
                        "Gaming Laptop",
                        "High-performance gaming laptop",
                        1299.99,
                        "Computers",
                        True,
                        15,
                    ),
                    (
                        "Wireless Mouse",
                        "Ergonomic wireless mouse",
                        29.99,
                        "Computers",
                        True,
                        50,
                    ),
                    (
                        "Mechanical Keyboard",
                        "RGB mechanical keyboard",
                        129.99,
                        "Computers",
                        True,
                        25,
                    ),
                    (
                        "Smartphone",
                        "Latest model smartphone",
                        799.99,
                        "Mobile",
                        True,
                        30,
                    ),
                    (
                        "Tablet",
                        "10-inch tablet with stylus",
                        399.99,
                        "Mobile",
                        False,
                        0,
                    ),
                    (
                        "Office Chair",
                        "Ergonomic office chair",
                        299.99,
                        "Furniture",
                        True,
                        10,
                    ),
                    (
                        "Standing Desk",
                        "Adjustable standing desk",
                        599.99,
                        "Furniture",
                        True,
                        5,
                    ),
                    (
                        "Python Programming Book",
                        "Comprehensive Python guide",
                        49.99,
                        "Books",
                        True,
                        20,
                    ),
                ]
                cursor.executemany(
                    "INSERT OR IGNORE INTO products (name, description, price, category, in_stock, quantity) VALUES (?, ?, ?, ?, ?, ?)",
                    products_data,
                )

                orders_data = [
                    (1, 1, 1, 1299.99, 1299.99, "completed"),
                    (1, 2, 2, 29.99, 59.98, "completed"),
                    (2, 4, 1, 799.99, 799.99, "pending"),
                    (3, 6, 1, 299.99, 299.99, "shipped"),
                    (5, 3, 1, 129.99, 129.99, "completed"),
                ]
                cursor.executemany(
                    "INSERT OR IGNORE INTO orders (user_id, product_id, quantity, unit_price, total_price, status) VALUES (?, ?, ?, ?, ?, ?)",
                    orders_data,
                )

                conn.commit()
                conn.close()

            record_metric("database_tables_created", 4)
            logger.info(f"Enhanced sample database created at {db_path}")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _register_tools(self):
        """Register MCP tools with enhanced monitoring"""

        @self.app.tool()
        async def filesystem_operation(
            input_data: FileOperationInput,
        ) -> Dict[str, Any]:
            """
            Perform filesystem operations (read, write, list, delete) with monitoring

            Args:
                input_data: FileOperationInput containing operation details

            Returns:
                Dict containing operation result
            """
            with time_operation(f"filesystem_{input_data.operation}"):
                try:
                    result = _filesystem_operation(input_data, data_path=self.data_path)

                    # Record metrics
                    record_metric(f"filesystem_{input_data.operation}_count", 1)
                    if result.get("success"):
                        record_metric("filesystem_success_count", 1)
                    else:
                        record_metric("filesystem_error_count", 1)

                    logger.info(
                        f"Filesystem operation {input_data.operation} on {input_data.path}: {'success' if result.get('success') else 'failed'}"
                    )
                    return result

                except Exception as e:
                    logger.error(f"Filesystem operation failed: {e}")
                    record_metric("filesystem_error_count", 1)
                    return {"error": str(e), "success": False}

        @self.app.tool()
        async def database_query(input_data: DatabaseQueryInput) -> Dict[str, Any]:
            """
            Execute database queries with monitoring and security

            Args:
                input_data: DatabaseQueryInput containing query details

            Returns:
                Dict containing query results
            """
            db_path = self.data_path / "sample.db"

            with time_operation("database_query"):
                try:
                    result = _execute_database_query(input_data, db_path=str(db_path))

                    # Record metrics
                    record_metric("database_query_count", 1)
                    if result.get("success"):
                        record_metric("database_success_count", 1)
                        if "rows" in result:
                            record_metric("database_rows_returned", len(result["rows"]))
                    else:
                        record_metric("database_error_count", 1)

                    logger.info(
                        f"Database query executed: {'success' if result.get('success') else 'failed'}"
                    )
                    return result

                except Exception as e:
                    logger.error(f"Database query failed: {e}")
                    record_metric("database_error_count", 1)
                    return {"error": str(e), "success": False}

        @self.app.tool()
        async def api_call(input_data: APICallInput) -> Dict[str, Any]:
            """
            Make HTTP API calls with monitoring and rate limiting

            Args:
                input_data: APICallInput containing request details

            Returns:
                Dict containing API response
            """
            with time_operation(f"api_call_{input_data.method.lower()}"):
                try:
                    result = await _api_call(input_data)

                    # Record metrics
                    record_metric(f"api_call_{input_data.method.lower()}_count", 1)
                    if result.get("success"):
                        record_metric("api_call_success_count", 1)
                        record_metric(
                            "api_response_status", result.get("status_code", 0)
                        )
                    else:
                        record_metric("api_call_error_count", 1)

                    logger.info(
                        f"API call {input_data.method} {input_data.url}: {'success' if result.get('success') else 'failed'}"
                    )
                    return result

                except Exception as e:
                    logger.error(f"API call failed: {e}")
                    record_metric("api_call_error_count", 1)
                    return {"error": str(e), "success": False}

    def _register_health_endpoints(self):
        """Register health check and monitoring endpoints"""

        @self.app.tool()
        async def health_check() -> Dict[str, Any]:
            """
            Perform comprehensive health check

            Returns:
                Dict containing health status
            """
            try:
                health_status = {
                    "status": "healthy",
                    "timestamp": str(asyncio.get_event_loop().time()),
                    "version": "1.0.0",
                    "environment": self.config.environment,
                }

                # Check database connectivity
                try:
                    db_path = self.data_path / "sample.db"
                    conn = sqlite3.connect(db_path)
                    conn.execute("SELECT 1")
                    conn.close()
                    health_status["database"] = "connected"
                except Exception:
                    health_status["database"] = "disconnected"
                    health_status["status"] = "degraded"

                # Check filesystem
                try:
                    self.data_path.exists()
                    health_status["filesystem"] = "accessible"
                except Exception:
                    health_status["filesystem"] = "inaccessible"
                    health_status["status"] = "degraded"

                record_metric("health_check_count", 1)
                return health_status

            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": str(asyncio.get_event_loop().time()),
                }

        @self.app.tool()
        async def get_metrics() -> Dict[str, Any]:
            """
            Get server metrics and statistics

            Returns:
                Dict containing metrics data
            """
            try:
                # Get performance metrics
                perf_summary = self.metrics.get_performance_summary(window_minutes=60)

                # Get specific metrics
                metrics_data = {
                    "performance": perf_summary,
                    "filesystem_ops": self.metrics.get_metrics_summary(
                        "filesystem_success_count", 60
                    ),
                    "database_ops": self.metrics.get_metrics_summary(
                        "database_success_count", 60
                    ),
                    "api_calls": self.metrics.get_metrics_summary(
                        "api_call_success_count", 60
                    ),
                    "health_checks": self.metrics.get_metrics_summary(
                        "health_check_count", 60
                    ),
                }

                return {
                    "success": True,
                    "metrics": metrics_data,
                    "timestamp": str(asyncio.get_event_loop().time()),
                }

            except Exception as e:
                logger.error(f"Failed to get metrics: {e}")
                return {"error": str(e), "success": False}

    def run(self, host: str = None, port: int = None):
        """Run the enhanced MCP server"""
        server_host = host or self.config.server.host
        server_port = port or self.config.server.port

        logger.info(f"Starting Enhanced MCP Server on {server_host}:{server_port}")

        try:
            self.app.run(
                host=server_host, port=server_port, debug=self.config.server.debug
            )
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise


def main():
    """Main entry point"""
    try:
        server = EnhancedMCPServer()
        server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
