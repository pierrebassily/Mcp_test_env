from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class MCPTool:
    """Represents an available MCP tool"""

    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPToolCall:
    """Represents a tool call request"""

    tool_name: str
    parameters: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class MCPToolResult:
    """Represents the result of a tool execution"""

    tool_name: str
    parameters: Dict[str, Any]
    result: Any
    success: bool
    execution_time: float
    timestamp: str
    error: Optional[str] = None
