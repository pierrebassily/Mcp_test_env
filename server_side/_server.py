import logging
import sqlite3
import json

from typing import Optional
from pathlib import Path
from typing import Dict, Any
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

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MCPServer:
    """FastMCP Server Experimental"""

    def __init__(self, data_path: str = "./data"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(exist_ok=True)
        self.app = FastMCP("AI Agent MCP Server Experimental")
        self._init_sample_database()
        self._register_tools()

    def _init_sample_database(self):
        """
        Intialize Sample Database with test data

        - Creating SQLite database at {db_path}
        - Creating tables and inserting sample data

        """
        db_path = self.data_path / "sample.db"

        try:
            with sqlite3.connect(str(db_path)) as conn:
                cursor = conn.cursor()

                # Create sample tables
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        status TEXT,
                        created_date TEXT
                    )
                """
                )

                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS research_data (
                        id INTEGER PRIMARY KEY,
                        topic TEXT NOT NULL,
                        content TEXT,
                        source TEXT,
                        relevance_score REAL,
                        created_date TEXT
                    )
                """
                )

                # Insert sample data if tables are empty
                cursor.execute("SELECT COUNT(*) FROM projects")
                if cursor.fetchone()[0] == 0:
                    sample_projects = [
                        (
                            1,
                            "AI Research Project",
                            "Research latest AI developments",
                            "active",
                            "2024-01-15",
                        ),
                        (
                            2,
                            "LangGraph Implementation",
                            "Build agent workflow system",
                            "in_progress",
                            "2024-02-01",
                        ),
                        (
                            3,
                            "MCP Integration",
                            "Integrate Model Context Protocol",
                            "completed",
                            "2024-03-01",
                        ),
                    ]

                    cursor.executemany(
                        "INSERT INTO projects (id, name, description, status, created_date) VALUES (?, ?, ?, ?, ?)",
                        sample_projects,
                    )

                    sample_research = [
                        (
                            1,
                            "Large Language Models",
                            "Latest developments in LLM architecture",
                            "ArXiv",
                            0.95,
                            "2024-03-15",
                        ),
                        (
                            2,
                            "AI Agents",
                            "Multi-agent systems and coordination",
                            "Research Paper",
                            0.88,
                            "2024-03-16",
                        ),
                        (
                            3,
                            "Tool Integration",
                            "Methods for AI tool integration",
                            "Blog Post",
                            0.72,
                            "2024-03-17",
                        ),
                    ]

                    cursor.executemany(
                        "INSERT INTO research_data (id, topic, content, source, relevance_score, created_date) VALUES (?, ?, ?, ?, ?, ?)",
                        sample_research,
                    )

                conn.commit()

            logger.info(f"Sample database initialized at {db_path}")

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

    def _register_tools(self):
        """Register all MCP tools"""

        @self.app.tool
        async def file_system(
            operation: str, path: str, content: Optional[str] = None
        ) -> str:
            """
            File system operations with security controls

            Args:
              - operation: operation_type (read, write, list, delete)
              - path: file path or directory
            """

            try:
                input_data = FileOperationInput(
                    operation=operation, path=path, content=content
                )
                result = _filesystem_operation(input_data)
                return json.dumps(result)
            except Exception as e:
                logger.error(f"File system operation failed: {e}")
                return json.dumps({"error": str(e)})

        @self.app.tool
        async def database_query(query: str, database: str = "main") -> str:
            """
            Execute SQL queries on the sample database

            Args:
                - query: SQL query to execute
                - database: Database name (default: main)
            """
            try:
                input_data = DatabaseQueryInput(query=query, database=database)
                result = await _execute_database_query(input_data)
                return json.dumps(result)
            except Exception as e:
                logger.error(f"Database query failed: {e}")
                return json.dumps({"error": str(e)})

        @self.app.tool
        async def api_client(
            url: str,
            method: str = "GET",
            headers: Optional[Dict[str, str]] = None,
            data: Optional[Dict[str, Any]] = None,
        ) -> str:
            """
            HTTP API client for external service integration

            Args:
                url: API endpoint URL
                method: HTTP method
                headers: Request headers
                data: Request data
            """
            try:
                input_data = APICallInput(
                    url=url, method=method, headers=headers, data=data
                )
                result = await _api_call(input_data)
                return json.dumps(result)
            except Exception as e:
                logger.error(f"API client tool error: {e}")
                return json.dumps({"error": str(e), "success": False})


def main():
    """Run the MCP server"""
    try:
        print("Starting MCP Server...")
        print("=" * 50)
        server = MCPServer()
        server.app.run()
    except KeyboardInterrupt:
        print("\nMCP Server stopped by user.")
    except Exception as e:
        logger.error(f"Server error: {e}")


if __name__ == "__main__":
    main()
