"""
Comprehensive integration tests for MCP Test Environment
"""

import asyncio
import sqlite3
import tempfile
import json
from pathlib import Path
from unittest import IsolatedAsyncioTestCase

from tests.framework import MCPTestFramework, TestSuite, performance_test
from server_side.utils.tools_functions import (
    _filesystem_operation,
    _execute_database_query,
    _api_call,
)
from server_side.utils.input_models import (
    FileOperationInput,
    DatabaseQueryInput,
    APICallInput,
)


class TestMCPIntegration(IsolatedAsyncioTestCase):
    """Integration tests for MCP components"""

    async def asyncSetUp(self):
        """Setup test environment"""
        self.framework = MCPTestFramework()
        self.env = self.framework.setup_test_environment()

    async def asyncTearDown(self):
        """Cleanup test environment"""
        self.framework.cleanup_test_environment()

    async def test_filesystem_operations_complete_workflow(self):
        """Test complete filesystem operations workflow"""
        data_path = self.env["test_files_dir"]

        # Test write operation
        write_input = FileOperationInput(
            operation="write",
            path="integration_test.txt",
            content="Integration test content",
        )
        result = _filesystem_operation(write_input, data_path=data_path)
        self.assertTrue(result.get("success", False))

        # Test read operation
        read_input = FileOperationInput(operation="read", path="integration_test.txt")
        result = _filesystem_operation(read_input, data_path=data_path)
        self.assertTrue(result.get("success", False))
        self.assertEqual(result.get("content"), "Integration test content")

        # Test list operation
        list_input = FileOperationInput(operation="list", path=".")
        result = _filesystem_operation(list_input, data_path=data_path)
        self.assertTrue(result.get("success", False))
        self.assertGreater(result.get("count", 0), 0)

        # Test delete operation
        delete_input = FileOperationInput(
            operation="delete", path="integration_test.txt"
        )
        result = _filesystem_operation(delete_input, data_path=data_path)
        self.assertTrue(result.get("success", False))

    async def test_database_operations_complete_workflow(self):
        """Test complete database operations workflow"""
        db_path = self.env["test_db_path"]

        # Test SELECT query
        select_query = DatabaseQueryInput(query="SELECT COUNT(*) as count FROM users")
        result = _execute_database_query(select_query, db_path=str(db_path))
        self.assertTrue(result.get("success", False))
        self.assertGreater(len(result.get("rows", [])), 0)

        # Test INSERT query
        insert_query = DatabaseQueryInput(
            query="INSERT INTO users (name, email) VALUES ('Test User', 'test@example.com')"
        )
        result = _execute_database_query(insert_query, db_path=str(db_path))
        self.assertTrue(result.get("success", False))

        # Test UPDATE query
        update_query = DatabaseQueryInput(
            query="UPDATE users SET name = 'Updated Test User' WHERE email = 'test@example.com'"
        )
        result = _execute_database_query(update_query, db_path=str(db_path))
        self.assertTrue(result.get("success", False))

        # Test DELETE query
        delete_query = DatabaseQueryInput(
            query="DELETE FROM users WHERE email = 'test@example.com'"
        )
        result = _execute_database_query(delete_query, db_path=str(db_path))
        self.assertTrue(result.get("success", False))

    async def test_api_call_operations(self):
        """Test API call operations"""
        # Test GET request to a mock endpoint
        get_request = APICallInput(
            url="https://httpbin.org/get",
            method="GET",
            headers={"User-Agent": "MCP-Test-Client/1.0"},
        )
        result = await _api_call(get_request)
        self.assertTrue(result.get("success", False))
        self.assertEqual(result.get("status_code"), 200)

        # Test POST request with data
        post_request = APICallInput(
            url="https://httpbin.org/post",
            method="POST",
            headers={"Content-Type": "application/json"},
            data={"test": "data", "number": 42},
        )
        result = await _api_call(post_request)
        self.assertTrue(result.get("success", False))
        self.assertEqual(result.get("status_code"), 200)

    @performance_test(max_duration=0.1, min_success_rate=0.99)
    async def test_filesystem_performance(self):
        """Performance test for filesystem operations"""
        data_path = self.env["test_files_dir"]

        # Write operation performance
        write_input = FileOperationInput(
            operation="write", path="perf_test.txt", content="Performance test content"
        )
        _filesystem_operation(write_input, data_path=data_path)

        # Read operation performance
        read_input = FileOperationInput(operation="read", path="perf_test.txt")
        _filesystem_operation(read_input, data_path=data_path)

    @performance_test(max_duration=0.05, min_success_rate=0.99)
    async def test_database_performance(self):
        """Performance test for database operations"""
        db_path = self.env["test_db_path"]

        query = DatabaseQueryInput(query="SELECT * FROM users LIMIT 10")
        _execute_database_query(query, db_path=str(db_path))

    async def test_error_handling(self):
        """Test error handling in various scenarios"""
        data_path = self.env["test_files_dir"]

        # Test reading non-existent file
        read_input = FileOperationInput(operation="read", path="non_existent_file.txt")
        result = _filesystem_operation(read_input, data_path=data_path)
        self.assertFalse(result.get("success", True))
        self.assertIn("error", result)

        # Test invalid database query
        db_path = self.env["test_db_path"]
        invalid_query = DatabaseQueryInput(query="INVALID SQL SYNTAX")
        result = _execute_database_query(invalid_query, db_path=str(db_path))
        self.assertFalse(result.get("success", True))
        self.assertIn("error", result)

    async def test_concurrent_operations(self):
        """Test concurrent operations handling"""
        data_path = self.env["test_files_dir"]

        # Create multiple concurrent file operations
        tasks = []
        for i in range(10):
            write_input = FileOperationInput(
                operation="write",
                path=f"concurrent_test_{i}.txt",
                content=f"Concurrent test content {i}",
            )
            task = asyncio.create_task(
                asyncio.to_thread(
                    _filesystem_operation, write_input, data_path=data_path
                )
            )
            tasks.append(task)

        # Wait for all operations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations succeeded
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.fail(f"Concurrent operation {i} failed with exception: {result}")
            else:
                self.assertTrue(
                    result.get("success", False), f"Concurrent operation {i} failed"
                )


class TestMCPStressTests(IsolatedAsyncioTestCase):
    """Stress tests for MCP components"""

    async def asyncSetUp(self):
        """Setup test environment"""
        self.framework = MCPTestFramework()
        self.env = self.framework.setup_test_environment()

    async def asyncTearDown(self):
        """Cleanup test environment"""
        self.framework.cleanup_test_environment()

    async def test_high_volume_filesystem_operations(self):
        """Test high volume filesystem operations"""
        data_path = self.env["test_files_dir"]
        operations_count = 100

        # Create multiple files
        for i in range(operations_count):
            write_input = FileOperationInput(
                operation="write",
                path=f"stress_test_{i}.txt",
                content=f"Stress test content {i}" * 100,  # Larger content
            )
            result = _filesystem_operation(write_input, data_path=data_path)
            self.assertTrue(result.get("success", False))

        # Read all files
        for i in range(operations_count):
            read_input = FileOperationInput(
                operation="read", path=f"stress_test_{i}.txt"
            )
            result = _filesystem_operation(read_input, data_path=data_path)
            self.assertTrue(result.get("success", False))

        # Clean up files
        for i in range(operations_count):
            delete_input = FileOperationInput(
                operation="delete", path=f"stress_test_{i}.txt"
            )
            result = _filesystem_operation(delete_input, data_path=data_path)
            self.assertTrue(result.get("success", False))

    async def test_database_transaction_stress(self):
        """Test database under stress with many transactions"""
        db_path = self.env["test_db_path"]
        operations_count = 100

        # Insert many records
        for i in range(operations_count):
            insert_query = DatabaseQueryInput(
                query=f"INSERT INTO users (name, email) VALUES ('Stress User {i}', 'stress{i}@example.com')"
            )
            result = _execute_database_query(insert_query, db_path=str(db_path))
            self.assertTrue(result.get("success", False))

        # Query records
        select_query = DatabaseQueryInput(
            query="SELECT COUNT(*) as count FROM users WHERE email LIKE 'stress%@example.com'"
        )
        result = _execute_database_query(select_query, db_path=str(db_path))
        self.assertTrue(result.get("success", False))
        count = result.get("rows", [{}])[0].get("count", 0)
        self.assertEqual(count, operations_count)

        # Clean up
        cleanup_query = DatabaseQueryInput(
            query="DELETE FROM users WHERE email LIKE 'stress%@example.com'"
        )
        result = _execute_database_query(cleanup_query, db_path=str(db_path))
        self.assertTrue(result.get("success", False))


# Test suite definitions
def create_integration_test_suite() -> TestSuite:
    """Create integration test suite"""
    test_class = TestMCPIntegration()

    return TestSuite(
        name="MCP Integration Tests",
        tests=[
            test_class.test_filesystem_operations_complete_workflow,
            test_class.test_database_operations_complete_workflow,
            test_class.test_api_call_operations,
            test_class.test_error_handling,
            test_class.test_concurrent_operations,
        ],
        setup_func=test_class.asyncSetUp,
        teardown_func=test_class.asyncTearDown,
        parallel=False,
        timeout=300,
    )


def create_performance_test_suite() -> TestSuite:
    """Create performance test suite"""
    test_class = TestMCPIntegration()

    return TestSuite(
        name="MCP Performance Tests",
        tests=[
            test_class.test_filesystem_performance,
            test_class.test_database_performance,
        ],
        setup_func=test_class.asyncSetUp,
        teardown_func=test_class.asyncTearDown,
        parallel=True,
        timeout=60,
    )


def create_stress_test_suite() -> TestSuite:
    """Create stress test suite"""
    test_class = TestMCPStressTests()

    return TestSuite(
        name="MCP Stress Tests",
        tests=[
            test_class.test_high_volume_filesystem_operations,
            test_class.test_database_transaction_stress,
        ],
        setup_func=test_class.asyncSetUp,
        teardown_func=test_class.asyncTearDown,
        parallel=False,
        timeout=600,
    )
