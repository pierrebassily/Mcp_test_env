"""
Mock services for isolated MCP testing
"""

import asyncio
import json
import sqlite3
import tempfile
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import aiohttp
from aiohttp import web

from utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MockResponse:
    """Mock HTTP response"""

    status_code: int
    content: str
    headers: Dict[str, str] = field(default_factory=dict)
    delay: float = 0.0  # Simulated network delay


@dataclass
class MockEndpoint:
    """Mock HTTP endpoint configuration"""

    path: str
    method: str
    response: MockResponse
    call_count: int = 0
    match_params: Optional[Dict[str, Any]] = None


class MockHTTPServer:
    """Mock HTTP server for testing API calls"""

    def __init__(self, host: str = "127.0.0.1", port: int = 8999):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.endpoints: List[MockEndpoint] = []
        self.server = None
        self.runner = None

    def add_endpoint(self, endpoint: MockEndpoint):
        """Add a mock endpoint"""
        self.endpoints.append(endpoint)

        async def handler(request):
            # Find matching endpoint
            for ep in self.endpoints:
                if (
                    ep.path == request.path
                    and ep.method.upper() == request.method.upper()
                ):

                    ep.call_count += 1

                    # Simulate delay if specified
                    if ep.response.delay > 0:
                        await asyncio.sleep(ep.response.delay)

                    # Log the call
                    logger.debug(
                        f"Mock endpoint called: {request.method} {request.path}"
                    )

                    return web.Response(
                        text=ep.response.content,
                        status=ep.response.status_code,
                        headers=ep.response.headers,
                    )

            # Default 404 response
            return web.Response(text="Not Found", status=404)

        # Add route for all methods
        self.app.router.add_route("*", endpoint.path, handler)

    async def start(self):
        """Start the mock server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

        logger.info(f"Mock HTTP server started at http://{self.host}:{self.port}")

    async def stop(self):
        """Stop the mock server"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("Mock HTTP server stopped")

    def get_base_url(self) -> str:
        """Get the base URL of the mock server"""
        return f"http://{self.host}:{self.port}"

    def get_endpoint_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for all endpoints"""
        return [
            {
                "path": ep.path,
                "method": ep.method,
                "call_count": ep.call_count,
                "response_status": ep.response.status_code,
            }
            for ep in self.endpoints
        ]


class MockDatabase:
    """Mock database for testing database operations"""

    def __init__(self):
        self.db_path = Path(tempfile.mktemp(suffix=".db"))
        self.connection = None
        self.query_log: List[Dict[str, Any]] = []

    def setup(self):
        """Setup mock database with test data"""
        self.connection = sqlite3.connect(self.db_path)
        cursor = self.connection.cursor()

        # Create test tables
        cursor.execute(
            """
            CREATE TABLE mock_users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE mock_posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                title TEXT NOT NULL,
                content TEXT,
                published BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES mock_users (id)
            )
        """
        )

        # Insert test data
        test_users = [
            ("testuser1", "test1@example.com"),
            ("testuser2", "test2@example.com"),
            ("admin", "admin@example.com"),
        ]
        cursor.executemany(
            "INSERT INTO mock_users (username, email) VALUES (?, ?)", test_users
        )

        test_posts = [
            (1, "First Post", "This is the first test post", True),
            (1, "Second Post", "This is the second test post", False),
            (2, "User 2 Post", "Post from user 2", True),
            (3, "Admin Post", "Administrative post", True),
        ]
        cursor.executemany(
            "INSERT INTO mock_posts (user_id, title, content, published) VALUES (?, ?, ?, ?)",
            test_posts,
        )

        self.connection.commit()
        logger.info(f"Mock database setup at {self.db_path}")

    def execute_query(
        self, query: str, params: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """Execute a query and return results"""
        if not self.connection:
            return {"error": "Database not initialized", "success": False}

        # Log the query
        self.query_log.append(
            {"query": query, "params": params, "timestamp": datetime.now().isoformat()}
        )

        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Handle different query types
            if query.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                return {
                    "success": True,
                    "rows": [dict(zip(columns, row)) for row in rows],
                    "column_names": columns,
                    "row_count": len(rows),
                }
            else:
                self.connection.commit()
                return {
                    "success": True,
                    "rows_affected": cursor.rowcount,
                    "last_row_id": cursor.lastrowid,
                }

        except Exception as e:
            logger.error(f"Mock database query failed: {e}")
            return {"error": str(e), "success": False}

    def get_query_log(self) -> List[Dict[str, Any]]:
        """Get the query execution log"""
        return self.query_log.copy()

    def cleanup(self):
        """Cleanup mock database"""
        if self.connection:
            self.connection.close()
        if self.db_path.exists():
            self.db_path.unlink()
        logger.info("Mock database cleaned up")


class MockFileSystem:
    """Mock filesystem for testing file operations"""

    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="mock_fs_"))
        self.operation_log: List[Dict[str, Any]] = []

    def setup(self):
        """Setup mock filesystem with test files"""
        # Create test directory structure
        (self.temp_dir / "documents").mkdir()
        (self.temp_dir / "images").mkdir()
        (self.temp_dir / "data").mkdir()

        # Create test files
        test_files = {
            "readme.txt": "This is a test readme file",
            "config.json": '{"debug": true, "version": "1.0.0"}',
            "documents/letter.txt": "Dear test user,\n\nThis is a test letter.\n\nBest regards,\nTest System",
            "documents/report.md": "# Test Report\n\nThis is a test report.\n\n## Results\n\nAll tests passed.",
            "data/sample.csv": "id,name,value\n1,test1,100\n2,test2,200\n3,test3,300",
        }

        for file_path, content in test_files.items():
            full_path = self.temp_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        logger.info(f"Mock filesystem setup at {self.temp_dir}")

    def execute_operation(
        self, operation: str, path: str, content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a filesystem operation"""
        full_path = self.temp_dir / path

        # Log the operation
        self.operation_log.append(
            {
                "operation": operation,
                "path": path,
                "timestamp": datetime.now().isoformat(),
            }
        )

        try:
            if operation == "read":
                if not full_path.exists():
                    return {"error": f"File {path} does not exist", "success": False}

                if full_path.is_file():
                    content = full_path.read_text()
                    return {
                        "success": True,
                        "content": content,
                        "size": len(content),
                        "path": str(full_path),
                    }
                else:
                    return {"error": f"Path {path} is not a file", "success": False}

            elif operation == "write":
                if content is None:
                    return {
                        "error": "Content required for write operation",
                        "success": False,
                    }

                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
                return {"success": True, "path": str(full_path), "size": len(content)}

            elif operation == "list":
                if not full_path.exists():
                    return {"error": f"Path {path} does not exist", "success": False}

                if full_path.is_dir():
                    items = []
                    for item in full_path.iterdir():
                        items.append(
                            {
                                "name": item.name,
                                "type": "directory" if item.is_dir() else "file",
                                "size": item.stat().st_size if item.is_file() else None,
                            }
                        )

                    return {
                        "success": True,
                        "items": items,
                        "count": len(items),
                        "path": str(full_path),
                    }
                else:
                    return {
                        "error": f"Path {path} is not a directory",
                        "success": False,
                    }

            elif operation == "delete":
                if not full_path.exists():
                    return {"error": f"Path {path} does not exist", "success": False}

                if full_path.is_file():
                    full_path.unlink()
                elif full_path.is_dir():
                    import shutil

                    shutil.rmtree(full_path)

                return {"success": True, "path": str(full_path)}

            else:
                return {"error": f"Unknown operation: {operation}", "success": False}

        except Exception as e:
            logger.error(f"Mock filesystem operation failed: {e}")
            return {"error": str(e), "success": False}

    def get_operation_log(self) -> List[Dict[str, Any]]:
        """Get the operation log"""
        return self.operation_log.copy()

    def cleanup(self):
        """Cleanup mock filesystem"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        logger.info("Mock filesystem cleaned up")


class MockMCPEnvironment:
    """Complete mock environment for MCP testing"""

    def __init__(self):
        self.http_server = MockHTTPServer()
        self.database = MockDatabase()
        self.filesystem = MockFileSystem()
        self._setup_default_endpoints()

    def _setup_default_endpoints(self):
        """Setup default mock endpoints"""
        # Success endpoint
        self.http_server.add_endpoint(
            MockEndpoint(
                path="/api/health",
                method="GET",
                response=MockResponse(
                    200, '{"status": "ok", "timestamp": "2023-01-01T00:00:00Z"}'
                ),
            )
        )

        # Error endpoint
        self.http_server.add_endpoint(
            MockEndpoint(
                path="/api/error",
                method="GET",
                response=MockResponse(500, '{"error": "Internal server error"}'),
            )
        )

        # Slow endpoint
        self.http_server.add_endpoint(
            MockEndpoint(
                path="/api/slow",
                method="GET",
                response=MockResponse(200, '{"message": "slow response"}', delay=2.0),
            )
        )

        # Echo endpoint
        self.http_server.add_endpoint(
            MockEndpoint(
                path="/api/echo",
                method="POST",
                response=MockResponse(200, '{"received": true}'),
            )
        )

    async def start(self):
        """Start all mock services"""
        await self.http_server.start()
        self.database.setup()
        self.filesystem.setup()
        logger.info("Mock MCP environment started")

    async def stop(self):
        """Stop all mock services"""
        await self.http_server.stop()
        self.database.cleanup()
        self.filesystem.cleanup()
        logger.info("Mock MCP environment stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from all mock services"""
        return {
            "http_endpoints": self.http_server.get_endpoint_stats(),
            "database_queries": len(self.database.get_query_log()),
            "filesystem_operations": len(self.filesystem.get_operation_log()),
            "http_base_url": self.http_server.get_base_url(),
        }
