"""
Enhanced test framework for MCP Test Environment
"""

import asyncio
import pytest
import pytest_asyncio
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3
import aiohttp
import time

from config.config import load_config
from utils.logging import get_logger
from utils.metrics import get_metrics_collector, time_operation

logger = get_logger(__name__)


@dataclass
class TestResult:
    """Test result data structure"""

    test_name: str
    success: bool
    duration: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TestSuite:
    """Test suite configuration"""

    name: str
    tests: List[Callable]
    setup_func: Optional[Callable] = None
    teardown_func: Optional[Callable] = None
    parallel: bool = False
    timeout: int = 300


class MCPTestFramework:
    """Enhanced test framework for MCP components"""

    def __init__(self):
        self.config = load_config()
        self.metrics = get_metrics_collector()
        self.test_results: List[TestResult] = []
        self.temp_dirs: List[Path] = []

    def setup_test_environment(self) -> Dict[str, Any]:
        """Setup test environment with temporary directories and test data"""
        # Create temporary directory for tests
        temp_dir = Path(tempfile.mkdtemp(prefix="mcp_test_"))
        self.temp_dirs.append(temp_dir)

        # Create test database
        test_db_path = temp_dir / "test.db"
        self._create_test_database(test_db_path)

        # Create test files
        test_files_dir = temp_dir / "files"
        test_files_dir.mkdir()
        self._create_test_files(test_files_dir)

        environment = {
            "temp_dir": temp_dir,
            "test_db_path": test_db_path,
            "test_files_dir": test_files_dir,
            "config": self.config,
        }

        logger.info(f"Test environment setup at {temp_dir}")
        return environment

    def cleanup_test_environment(self):
        """Cleanup test environment"""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up test directory {temp_dir}")
        self.temp_dirs.clear()

    def _create_test_database(self, db_path: Path):
        """Create test database with sample data"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create test tables
        cursor.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                category TEXT NOT NULL,
                in_stock BOOLEAN DEFAULT TRUE
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                product_id INTEGER,
                quantity INTEGER,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        """
        )

        # Insert test data
        test_users = [
            ("Alice Johnson", "alice@example.com"),
            ("Bob Smith", "bob@example.com"),
            ("Charlie Brown", "charlie@example.com"),
        ]
        cursor.executemany("INSERT INTO users (name, email) VALUES (?, ?)", test_users)

        test_products = [
            ("Laptop", 999.99, "Electronics", True),
            ("Mouse", 29.99, "Electronics", True),
            ("Keyboard", 79.99, "Electronics", False),
            ("Desk Chair", 199.99, "Furniture", True),
        ]
        cursor.executemany(
            "INSERT INTO products (name, price, category, in_stock) VALUES (?, ?, ?, ?)",
            test_products,
        )

        test_orders = [(1, 1, 2), (1, 2, 1), (2, 1, 1), (3, 4, 1)]
        cursor.executemany(
            "INSERT INTO orders (user_id, product_id, quantity) VALUES (?, ?, ?)",
            test_orders,
        )

        conn.commit()
        conn.close()

    def _create_test_files(self, files_dir: Path):
        """Create test files for filesystem operations"""
        # Create various test files
        (files_dir / "test.txt").write_text("Hello, World!")
        (files_dir / "data.json").write_text('{"test": true, "value": 42}')
        (files_dir / "config.yaml").write_text("debug: true\nport: 8000\n")

        # Create subdirectory with files
        subdir = files_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("Nested file content")
        (subdir / "empty.txt").write_text("")

    async def run_test_suite(self, test_suite: TestSuite) -> List[TestResult]:
        """Run a test suite and return results"""
        suite_results = []

        logger.info(f"Running test suite: {test_suite.name}")

        # Setup
        if test_suite.setup_func:
            try:
                await test_suite.setup_func()
            except Exception as e:
                logger.error(f"Setup failed for {test_suite.name}: {e}")
                return suite_results

        # Run tests
        if test_suite.parallel:
            tasks = []
            for test_func in test_suite.tests:
                task = asyncio.create_task(
                    self._run_single_test(test_func, test_suite.timeout)
                )
                tasks.append(task)

            suite_results = await asyncio.gather(*tasks, return_exceptions=True)
            suite_results = [r for r in suite_results if isinstance(r, TestResult)]
        else:
            for test_func in test_suite.tests:
                result = await self._run_single_test(test_func, test_suite.timeout)
                suite_results.append(result)

        # Teardown
        if test_suite.teardown_func:
            try:
                await test_suite.teardown_func()
            except Exception as e:
                logger.error(f"Teardown failed for {test_suite.name}: {e}")

        self.test_results.extend(suite_results)
        return suite_results

    async def _run_single_test(self, test_func: Callable, timeout: int) -> TestResult:
        """Run a single test function"""
        test_name = test_func.__name__

        with time_operation(f"test_{test_name}"):
            start_time = time.time()
            try:
                # Run test with timeout
                if asyncio.iscoroutinefunction(test_func):
                    await asyncio.wait_for(test_func(), timeout=timeout)
                else:
                    test_func()

                duration = time.time() - start_time
                result = TestResult(test_name, True, duration)
                logger.info(f"Test {test_name} PASSED in {duration:.3f}s")

            except asyncio.TimeoutError:
                duration = time.time() - start_time
                result = TestResult(test_name, False, duration, "Test timed out")
                logger.error(f"Test {test_name} TIMEOUT after {duration:.3f}s")

            except Exception as e:
                duration = time.time() - start_time
                result = TestResult(test_name, False, duration, str(e))
                logger.error(f"Test {test_name} FAILED: {e}")

        return result

    def generate_test_report(self, output_path: str):
        """Generate comprehensive test report"""
        report = {
            "summary": self._generate_test_summary(),
            "results": [
                {
                    "test_name": r.test_name,
                    "success": r.success,
                    "duration": r.duration,
                    "error_message": r.error_message,
                    "timestamp": r.timestamp.isoformat(),
                    "metadata": r.metadata,
                }
                for r in self.test_results
            ],
            "metrics": self._get_test_metrics(),
            "generated_at": datetime.now().isoformat(),
        }

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Test report generated: {output_path}")

    def _generate_test_summary(self) -> Dict[str, Any]:
        """Generate test summary statistics"""
        if not self.test_results:
            return {"total": 0, "passed": 0, "failed": 0, "success_rate": 0}

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - passed_tests

        total_duration = sum(r.duration for r in self.test_results)
        avg_duration = total_duration / total_tests

        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": passed_tests / total_tests,
            "total_duration": total_duration,
            "average_duration": avg_duration,
        }

    def _get_test_metrics(self) -> Dict[str, Any]:
        """Get test-related metrics"""
        return {
            "performance_summary": self.metrics.get_performance_summary(
                window_minutes=60
            ),
            "test_metrics": self.metrics.get_metrics_summary(
                "test_execution", window_minutes=60
            ),
        }


# Fixture for test framework
@pytest.fixture
async def test_framework():
    """Pytest fixture for test framework"""
    framework = MCPTestFramework()
    env = framework.setup_test_environment()
    yield framework, env
    framework.cleanup_test_environment()


# Performance test decorator
def performance_test(max_duration: float = 1.0, min_success_rate: float = 0.95):
    """Decorator for performance tests"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            success_count = 0
            total_runs = 10

            for _ in range(total_runs):
                try:
                    if asyncio.iscoroutinefunction(func):
                        await func(*args, **kwargs)
                    else:
                        func(*args, **kwargs)
                    success_count += 1
                except Exception:
                    pass

            duration = (time.time() - start_time) / total_runs
            success_rate = success_count / total_runs

            assert (
                duration <= max_duration
            ), f"Average duration {duration:.3f}s exceeds limit {max_duration}s"
            assert (
                success_rate >= min_success_rate
            ), f"Success rate {success_rate:.2%} below limit {min_success_rate:.2%}"

            return duration, success_rate

        return wrapper

    return decorator
