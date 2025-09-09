import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import MCP client components
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from utils.mcp_tools_models import MCPTool, MCPToolCall, MCPToolResult
from utils.utils import _format_parameters_for_tool, _parse_tool_result


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MCPClient:
    """Client for interacting with the MCP server"""

    def __init__(self, server_script: str = "server_side\server.py"):
        self.server_script = server_script
        self.server_parameters = None
        self.timeout = 30
        self._connected = False
        self.available_tools: List[Dict[str, MCPTool]] = []

    async def connect(self):
        """Connect to the MCP server using stdio"""
        try:
            self.server_parameters = StdioServerParameters(
                command="python",
                args=[self.server_script],
                env=None,
            )

            await asyncio.wait_for(self.discover_tools(), timeout=self.timeout)
            self._connected = True
            logger.info(f"Connected to MCP server {self.server_script} successfully.")
            return True
        except asyncio.TimeoutError:
            logger.error(
                f"Connection to MCP server timed out after {self.timeout} seconds."
            )
            return False
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the MCP server"""
        self._connected = False
        logger.info("Disconnected from MCP server.")

    def is_connected(self) -> bool:
        """Check if the client is connected to the server"""
        return self._connected

    async def discover_tools(self):
        """Discover available tools from the MCP server"""
        try:
            if not self.server_parameters:
                self.server_parameters = StdioServerParameters(
                    command="python",
                    args=[self.server_script],
                    env=None,
                )

            async with stdio_client(self.server_parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_response = await session.list_tools()

                    self.available_tools = {}

                    if hasattr(tools_response, "tools") and tools_response.tools:
                        for tool in tools_response.tools:
                            self.available_tools[tool.name] = MCPTool(
                                name=tool.name,
                                description=tool.description
                                or "No description available",
                                input_schema=(
                                    tool.inputSchema if tool.inputSchema else {}
                                ),
                            )
            logger.info(
                f"Discovered tools from MCP server: {len(self.available_tools)} tools available."
            )
            logger.debug(f"Available tools: {self.available_tools}")
            return list(self.available_tools.values())
        except Exception as e:
            logger.error(f"Failed to discover tools: {e}")
            return []

    async def get_available_tools(self) -> List[MCPTool]:
        """Get list of available tools"""
        if not self.available_tools:
            await self.discover_tools()
        return list(self.available_tools.values())

    def get_tool_info(self, tool_name: str) -> Optional[MCPTool]:
        """Get information about a specific tool"""
        return self.available_tools.get(tool_name)

    async def call_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> MCPToolResult:
        """Execute a tool call on MCP Server with the given parameters"""
        start_time = datetime.now()

        try:
            if not self._connected or not self.server_parameters:
                raise RuntimeError("Client is not connected to the MCP server.")
            if tool_name not in self.available_tools:
                raise ValueError(
                    f"Tool '{tool_name}' is not available on the MCP server."
                )

            formattted_parameters = _format_parameters_for_tool(tool_name, parameters)

            async with stdio_client(self.server_parameters) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    result = await asyncio.wait_for(
                        session.call_tool(tool_name, formattted_parameters),
                        timeout=self.timeout,
                    )
                    execution_time = (datetime.now() - start_time).total_seconds()

                    result_data = _parse_tool_result(result)

                    success = True
                    error = None

                    if isinstance(result_data, dict):
                        success = result_data.get(
                            "success", not bool(result_data.get("error"))
                        )
                        error = result_data.get("error")

                    return MCPToolResult(
                        tool_name=tool_name,
                        parameters=parameters,
                        result=result_data,
                        success=success,
                        execution_time=execution_time,
                        timestamp=datetime.now().isoformat(),
                        error=error,
                    )
        except Exception as e:
            logger.error(f"Tool call failed for '{tool_name}': {e}")
            return MCPToolResult(
                tool_name=tool_name,
                parameters=parameters,
                result=None,
                success=False,
                execution_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now().isoformat(),
                error=str(e),
            )

    async def call_multiple_tools(
        self, tool_calls: List[MCPToolCall]
    ) -> List[MCPToolResult]:
        """Execute multiple tool calls in sequence"""
        results = []

        for tool_call in tool_calls:
            result = await self.call_tool(tool_call.tool_name, tool_call.parameters)
            results.append(result)

            # Log progress
            status = "✅" if result.success else "❌"
            logger.info(f"{status} {tool_call.tool_name}: {result.execution_time:.2f}s")

            # Small delay between calls
            await asyncio.sleep(0.1)

        return results


async def demo_client():
    print("Starting MCP Client demo...")
    print("=" * 50)
    client = MCPClient(server_script="server_side/server.py")

    if not await client.connect():
        print("Failed to connect to MCP server.")

    print("Connected to MCP server.")
    tools = await client.get_available_tools()
    print(f"Available tools: {len(tools)}")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")

    print("demo is working")
    await client.disconnect()
    print("Disconnected from MCP server.")


if __name__ == "__main__":
    asyncio.run(demo_client())
