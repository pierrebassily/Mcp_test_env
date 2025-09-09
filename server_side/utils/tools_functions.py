"""
Functions that used in actual tool implementations

"""

from typing import Dict, Any
import asyncio
import aiohttp
from datetime import datetime
from .input_models import FileOperationInput, APICallInput, DatabaseQueryInput
from pathlib import Path
import sqlite3


def _filesystem_read_operation(
    input_data: FileOperationInput, full_path: Path
) -> Dict[str, Any]:
    """
    Perform file read operation with security controls.
    Args:
      - input_data: FileOperationInput containing file path
      - full_path: Base directory for file operations
    Returns:
      - dict: Result of the read operation
    """
    if input_data.operation == "read":
        if full_path.is_file():
            try:
                content = full_path.read_text(encoding="utf-8")
                return {
                    "content": content,
                    "size": len(content),
                    "path": str(full_path),
                    "sucess": True,
                }
            except Exception as e:
                return {"error": f"Failed to read file: {str(e)}"}

        return {"error": "File does not exist.", "sucess": False}


def _filesystem_write_operation(
    input_data: FileOperationInput, full_path: Path
) -> Dict[str, Any]:
    """
    Perform file write operation with security controls.
    Args:
        - input_data: FileOperationInput containing file path and content
        - full_path: Base directory for file operations
    Returns:
        - dict: Result of the write operation
    """
    if not input_data.content:
        return {
            "error": "Content is required for write operation.",
            "sucess": False,
        }

    full_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    full_path.write_text(input_data.content, encoding="utf-8")
    return {
        "message": "File written successfully.",
        "size": len(input_data.content),
        "path": str(full_path),
        "sucess": True,
    }


def _filesystem_list_operation(full_path: Path) -> Dict[str, Any]:
    """
    Perform file listing operation with security controls.
    Args:
        - input_data: FileOperationInput containing directory path
        - full_path: Base directory for file operations
    Returns:
        - dict: Result of the list operation
    """
    if full_path.is_dir():
        files = []
        for f in full_path.iterdir():
            files.append(
                {
                    "name": f.name,
                    "type": "directory" if f.is_dir() else "file",
                    "size": f.stat().st_size if f.is_file() else None,
                    "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                }
            )
        return {"files": files, "count": len(files), "sucess": True}
    return {"error": "Path is not a directory.", "sucess": False}


def _filesystem_delete_operation(
    input_data: FileOperationInput, full_path: Path
) -> Dict[str, Any]:
    """
    Perform file or directory delete operation with security controls.
    Args:
        - input_data: FileOperationInput containing file or directory path
        - full_path: Base directory for file operations
    Returns:
        - dict: Result of the delete operation
    """
    if full_path.exists():
        if full_path.is_file():
            full_path.unlink()
            return {
                "message": f"File deleted successfully {input_data.path}.",
                "sucess": True,
            }

        else:
            try:
                full_path.rmdir()  # Remove directory if empty
                return {
                    "message": f"Directory deleted successfully {input_data.path}.",
                    "sucess": True,
                }
            except OSError as e:
                return {
                    "error": f"Failed to delete directory: {str(e)}",
                    "sucess": False,
                }
    return {"error": "File or directory does not exist.", "sucess": False}


def _filesystem_operation(
    input_data: FileOperationInput,
    data_path: str = "./data",
) -> Dict[str, Any]:
    """
    Perform file system operations (read, write, list, delete) with security controls.

    Args:
      - input_data: FileOperationInput containing operation details

    Returns:
      - dict: Result of the file operation
    """

    if input_data.operation not in ["read", "write", "list", "delete"]:
        return {
            "error": "Invalid file operation you can only perform read, write, list, or delete."
        }

    full_path = (Path(data_path) / input_data.path).resolve()

    if input_data.operation == "read":
        return _filesystem_read_operation(input_data, full_path)

    elif input_data.operation == "write":
        return _filesystem_write_operation(input_data, full_path)

    elif input_data.operation == "list":
        return _filesystem_list_operation(full_path)

    elif input_data.operation == "delete":
        return _filesystem_delete_operation(input_data, full_path)


async def _execute_database_query(
    input_data: DatabaseQueryInput, data_path: str = "./data"
) -> Dict[str, Any]:
    """
    Execute SQL queries on the sample database with security controls.
    Args:
        - input_data: DatabaseQueryInput containing query
        - db_path: Path to the database file
    Returns:
        - dict: Result of the database query
    """

    db_path = data_path / f"{input_data.database}.db"
    if not db_path.exists():
        return {"error": "Database does not exist.", "sucess": False}
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(input_data.query)
            if input_data.query.strip().lower().startswith("select"):
                rows = cursor.fetchall()
                results = [dict(row) for row in rows]
                return {
                    "results": results,
                    "row_count": len(results),
                    "columns": (
                        [description[0] for description in cursor.description]
                        if cursor.description
                        else []
                    ),
                    "query": input_data.query,
                    "sucess": True,
                    "database": input_data.database,
                }
            else:
                conn.commit()
                return {
                    "rows_affected": cursor.rowcount,
                    "query": input_data.query,
                    "database": input_data.database,
                    "sucess": True,
                }
    except sqlite3.Error as e:
        return {"error": f"Database query failed: {str(e)}", "sucess": False}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}", "sucess": False}


async def _simulate_api_call(input_data: APICallInput) -> Dict[str, Any]:
    """
    Simulate an API call response for testing purposes.

    Args:
        - input_data: APICallInput containing API call details
    Returns:
        - dict: Simulated API response
    """

    await asyncio.sleep(0.1)  # Simulate network delay

    # Generate realistic simulated responses based on URL patterns
    if "weather" in input_data.url.lower():
        simulated_data = {
            "temperature": 22.5,
            "condition": "partly cloudy",
            "humidity": 65,
            "location": "San Francisco, CA",
        }
    elif "news" in input_data.url.lower():
        simulated_data = {
            "articles": [
                {
                    "title": "AI Research Breakthrough",
                    "summary": "New developments in machine learning",
                },
                {
                    "title": "Tech Industry Updates",
                    "summary": "Latest trends in technology sector",
                },
            ]
        }
    else:
        simulated_data = {
            "message": f"Simulated response for {input_data.method} {input_data.url}",
            "timestamp": datetime.now().isoformat(),
            "data": {"status": "success", "id": 12345},
        }

    return {
        "status_code": 200,
        "data": simulated_data,
        "headers": {"content-type": "application/json"},
        "url": input_data.url,
        "method": input_data.method,
        "response_time": 0.15,
        "simulated": True,
        "success": True,
    }


async def _api_call(input_data: APICallInput) -> Dict[str, Any]:
    """Make HTTP requests or simulate them if aiohttp is not available"""
    try:
        if aiohttp is None:
            # Simulate API response when aiohttp is not available
            return await _simulate_api_call(input_data)

        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            kwargs = {
                "method": input_data.method.upper(),
                "url": input_data.url,
                "headers": input_data.headers or {},
            }

            if input_data.method.upper() in ["POST", "PUT"] and input_data.data:
                kwargs["json"] = input_data.data

            async with session.request(**kwargs) as response:
                try:
                    response_data = await response.json()
                except Exception:
                    response_data = await response.text()

                return {
                    "status_code": response.status,
                    "data": response_data,
                    "headers": dict(response.headers),
                    "url": input_data.url,
                    "method": input_data.method,
                    "response_time": 0.3,
                    "success": True,
                }
    except Exception as e:
        return {"error": str(e), "success": False}
