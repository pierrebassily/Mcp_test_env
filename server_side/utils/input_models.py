"""
Input Models For MCP Tools

"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class FileOperationInput(BaseModel):
    operation: str = Field(..., description="Operation: read, write, list, delete")
    path: str = Field(..., description="File or directory path")
    content: Optional[str] = Field(None, description="Content for write operations")


class DatabaseQueryInput(BaseModel):
    query: str = Field(..., description="SQL query to execute")
    database: str = Field("main", description="Database name")


class APICallInput(BaseModel):
    url: str = Field(..., description="API endpoint URL")
    method: str = Field("GET", description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(None, description="Request headers")
    data: Optional[Dict[str, Any]] = Field(None, description="Request data")
