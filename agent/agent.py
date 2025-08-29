#!/usr/bin/env python3
"""
Fixed LangGraph Agent with Bedrock and FastMCP Integration
File: fixed_agent.py

Key fixes:
1. Correct MCP client usage with STDIO server
2. Fixed async/sync issues
3. Better error handling and recovery
4. Proper parameter formatting for FastMCP
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, TypedDict, Annotated
from datetime import datetime
import sys

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_aws import ChatBedrock

from client_side.utils.mcp_tools_models import MCPToolResult
from client_side.client import MCPClient

from utils import (
    _format_tools_for_prompt,
    _format_results_for_prompt,
    _parse_json_response,
)


# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Agent State Definition
class AgentState(TypedDict):
    messages: Annotated[List, add_messages]
    current_task: str
    selected_tools: List[Dict[str, Any]]
    tool_results: List[MCPToolResult]
    context: Dict[str, Any]
    step_count: int
    max_steps: int
    final_response: str


class BedrockMCPAgent:
    """
    AI Agent using AWS Bedrock and FastMCP

    """

    def __init__(
        self,
        model_id: str = "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        mcp_server_script: str = "server_side\server.py",
        aws_region: str = "us-east-1",
        max_steps: int = 10,
    ):
        self.model_id = model_id
        self.mcp_server_script = mcp_server_script
        self.aws_region = aws_region
        self.max_steps = max_steps

        # Initialize Bedrock LLM
        self.llm = self._initialize_bedrock_llm()

        # Initialize MCP client with STDIO server script
        self.mcp_client = MCPClient(
            server_script=self.mcp_server_script,
        )

        # Create the LangGraph workflow
        self.workflow = self._create_workflow()

        logger.info(
            f"Fixed agent initialized with model {model_id} and server {mcp_server_script}"
        )

    def _initialize_bedrock_llm(self) -> ChatBedrock:
        """Initialize AWS Bedrock LLM client with proper error handling"""
        try:
            # Load environment variables if available
            try:
                from dotenv import load_dotenv

                load_dotenv(".env")
                logger.info("Loaded environment variables from .env")
            except ImportError:
                logger.info("python-dotenv not available, using system environment")

            # Get AWS credentials from environment
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_session_token = os.getenv("AWS_SESSION_TOKEN")

            kwargs = {
                "model_id": self.model_id,
                "region_name": self.aws_region,
                "model_kwargs": {
                    "max_tokens": 4000,
                    "temperature": 0.1,
                    "top_p": 0.9,
                },
            }

            if aws_access_key and aws_secret_key:
                kwargs.update(
                    {
                        "aws_access_key_id": aws_access_key,
                        "aws_secret_access_key": aws_secret_key,
                    }
                )
                if aws_session_token:
                    kwargs["aws_session_token"] = aws_session_token
                logger.info("Using credentials from environment variables")
            else:
                logger.info("Using default AWS credential chain")

            return ChatBedrock(**kwargs)

        except Exception as e:
            logger.error(f"Failed to initialize Bedrock LLM: {str(e)}")
            raise

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow with proper error handling"""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("analyze_request", self._analyze_request_node)
        workflow.add_node("execute_tools", self._execute_tools_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("error_recovery", self._error_recovery_node)

        # Add edges with better error handling
        workflow.add_edge("analyze_request", "execute_tools")
        workflow.add_conditional_edges(
            "execute_tools",
            self._should_continue_execution,
            {
                "continue": "execute_tools",
                "respond": "generate_response",
                "error": "error_recovery",
            },
        )
        workflow.add_edge("generate_response", END)
        workflow.add_edge("error_recovery", "generate_response")

        # Set entry point
        workflow.set_entry_point("analyze_request")

        return workflow

    async def _analyze_request_node(self, state: AgentState) -> AgentState:
        """Analyze user request and determine required tools with better error handling"""
        try:
            user_message = state["messages"][-1].content
            context = state["context"]

            # Try to connect to MCP server
            try:
                connected = await self.mcp_client.connect()
                if not connected:
                    logger.warning(
                        "Could not connect to MCP server, proceeding without tools"
                    )
                    state["selected_tools"] = []
                    error_message = AIMessage(
                        content="Warning: Could not connect to MCP server. Proceeding with basic capabilities only."
                    )
                    state["messages"].append(error_message)
                    state["step_count"] += 1
                    return state
            except Exception as e:
                logger.error(f"MCP connection failed: {e}")
                state["selected_tools"] = []
                error_message = AIMessage(
                    content=f"Warning: MCP server connection failed ({str(e)}). Proceeding with basic capabilities only."
                )
                state["messages"].append(error_message)
                state["step_count"] += 1
                return state

            # Get available tools
            try:
                available_tools = await self.mcp_client.get_available_tools()
                logger.info(
                    f"Available tools: {[tool.name for tool in available_tools]}"
                )
            except Exception as e:
                logger.error(f"Failed to get available tools: {e}")
                available_tools = []

            # Create analysis prompt
            tools_description = _format_tools_for_prompt(available_tools)

            analysis_prompt = f"""
You are an expert AI agent that analyzes user requests and selects appropriate MCP tools.

Available Tools:
{tools_description}

User Request: {user_message}

Context: {json.dumps(context, indent=2)}

Analyze this request and provide a JSON response with your analysis and tool selection.

Response format (must be valid JSON):
{{
    "task_analysis": "Brief description of what the user wants to accomplish",
    "complexity": "simple",
    "selected_tools": [
        {{
            "tool": "tool_name",
            "parameters": {{"param_name": "param_value"}},
            "reason": "Why this tool is needed",
            "sequence": 1,
            "critical": false
        }}
    ],
    "execution_plan": "Brief plan for executing the tools",
    "expected_outcome": "What the user should expect"
}}

Rules for tool selection:
- Only use tools that are actually available
- Use minimum necessary tools to accomplish the task
- For research requests: use web_search first, then filesystem to save results
- For file operations: use filesystem tool
- For data queries: use database tool
- For code: use code_execution tool
- For API calls: use api_client tool

Be strategic and only select tools you are confident will help accomplish the user's goal.
"""

            # Get analysis from Bedrock
            try:
                response = await self.llm.ainvoke(
                    [
                        SystemMessage(
                            content="You are a strategic tool selection AI that responds only with valid JSON."
                        ),
                        HumanMessage(content=analysis_prompt),
                    ]
                )

                # Parse the JSON response
                analysis = _parse_json_response(response.content)

            except Exception as e:
                logger.error(f"Bedrock analysis failed: {e}")
                # Create fallback analysis
                analysis = {
                    "task_analysis": f"Process user request: {user_message[:100]}",
                    "complexity": "simple",
                    "selected_tools": self._create_fallback_tools(user_message),
                    "execution_plan": "Execute tools in sequence",
                    "expected_outcome": "Provide results to user",
                }

            # Update state
            state["current_task"] = analysis.get("task_analysis", "Processing request")
            state["selected_tools"] = analysis.get("selected_tools", [])

            # Add analysis message
            analysis_message = AIMessage(
                content=f"Analysis Complete\n"
                f"Task: {analysis.get('task_analysis', '')}\n"
                f"Tools selected: {len(state['selected_tools'])}\n"
                f"Plan: {analysis.get('execution_plan', '')}"
            )

            state["messages"].append(analysis_message)
            state["step_count"] += 1

            logger.info(
                f"Analysis complete - Selected {len(state['selected_tools'])} tools"
            )
            return state

        except Exception as e:
            logger.error(f"Request analysis failed: {str(e)}")
            # Create error recovery state
            state["selected_tools"] = []
            error_message = AIMessage(
                content=f"Analysis encountered an error: {str(e)}. Will attempt to provide a basic response."
            )
            state["messages"].append(error_message)
            state["step_count"] += 1
            return state

    async def _execute_tools_node(self, state: AgentState) -> AgentState:
        """Execute the selected MCP tools with improved error handling"""
        try:
            if not state["selected_tools"]:
                logger.info("No tools selected for execution")
                # Add a message indicating no tools were used
                no_tools_message = AIMessage(
                    content="No external tools needed for this request."
                )
                state["messages"].append(no_tools_message)
                state["step_count"] += 1
                return state

            # Execute tools in sequence order
            tools_to_execute = sorted(
                state["selected_tools"], key=lambda x: x.get("sequence", 0)
            )

            execution_results = []
            successful_executions = 0

            for i, tool_spec in enumerate(tools_to_execute):
                tool_name = tool_spec["tool"]
                parameters = tool_spec["parameters"]
                is_critical = tool_spec.get("critical", False)

                logger.info(
                    f"Executing tool {i+1}/{len(tools_to_execute)}: {tool_name}"
                )

                try:
                    # Execute the tool with timeout
                    result = await asyncio.wait_for(
                        self.mcp_client.call_tool(tool_name, parameters),
                        timeout=120,  # 2 minute timeout per tool
                    )
                    execution_results.append(result)

                    if result.success:
                        successful_executions += 1
                        logger.info(f"✅ {tool_name} completed successfully")
                    else:
                        logger.error(f"❌ {tool_name} failed: {result.error}")

                        # If critical tool fails, stop execution
                        if is_critical:
                            logger.error(
                                f"Critical tool {tool_name} failed, stopping execution"
                            )
                            break

                except asyncio.TimeoutError:
                    logger.error(f"❌ {tool_name} timed out")
                    # Create timeout result
                    timeout_result = MCPToolResult(
                        tool_name=tool_name,
                        parameters=parameters,
                        result={"error": "Tool execution timed out"},
                        success=False,
                        execution_time=120.0,
                        timestamp=datetime.now().isoformat(),
                        error="Tool execution timed out",
                    )
                    execution_results.append(timeout_result)

                    if is_critical:
                        logger.error(
                            f"Critical tool {tool_name} timed out, stopping execution"
                        )
                        break

                except Exception as e:
                    logger.error(f"❌ {tool_name} execution error: {e}")
                    # Create error result
                    error_result = MCPToolResult(
                        tool_name=tool_name,
                        parameters=parameters,
                        result={"error": str(e)},
                        success=False,
                        execution_time=0.0,
                        timestamp=datetime.now().isoformat(),
                        error=str(e),
                    )
                    execution_results.append(error_result)

                    if is_critical:
                        logger.error(
                            f"Critical tool {tool_name} failed, stopping execution"
                        )
                        break

                # Small delay between tools
                if i < len(tools_to_execute) - 1:
                    await asyncio.sleep(0.5)

            # Update state with results
            state["tool_results"] = execution_results

            # Create execution summary message
            execution_message = AIMessage(
                content=f"Tool Execution Complete\n"
                f"Successful: {successful_executions}/{len(tools_to_execute)}\n"
                f"Results ready for response generation"
            )

            state["messages"].append(execution_message)
            state["step_count"] += 1

            logger.info(
                f"Tool execution complete - {successful_executions}/{len(tools_to_execute)} successful"
            )
            return state

        except Exception as e:
            logger.error(f"Tool execution node failed: {str(e)}")
            error_message = AIMessage(
                content=f"Tool execution encountered an error: {str(e)}"
            )
            state["messages"].append(error_message)
            state["step_count"] += 1
            return state

    async def _generate_response_node(self, state: AgentState) -> AgentState:
        """Generate comprehensive response based on tool results"""
        try:
            original_request = state["messages"][0].content
            tool_results = state["tool_results"]

            # Check if we have any tool results
            if not tool_results:
                # Handle case with no tools executed
                try:
                    response = await self.llm.ainvoke(
                        [
                            SystemMessage(content="You are a helpful AI assistant."),
                            HumanMessage(
                                content=f"The user asked: '{original_request}'\n\nNo external tools were used. Provide a helpful response based on your knowledge."
                            ),
                        ]
                    )
                    final_response = response.content
                except Exception as e:
                    logger.error(f"Direct response generation failed: {e}")
                    final_response = f"I understand you're asking about: {original_request}\n\nI encountered some technical difficulties, but I'm here to help. Could you please rephrase your request or ask something specific I can assist with?"
            else:
                # Format tool results for the prompt
                results_summary = _format_results_for_prompt(tool_results)

                response_prompt = f"""
Generate a comprehensive, helpful response to the user based on the tool execution results.

Original User Request: {original_request}

Tool Execution Results:
{results_summary}

Guidelines for the response:
1. Directly address the user's original request
2. Highlight successful operations and key findings
3. Mention any errors or limitations encountered
4. Provide actionable information or next steps
5. Be conversational and user-friendly
6. Include relevant details from the tool outputs
7. If files were created, mention their locations
8. If data was found, summarize key insights

Create a response that feels natural and complete, as if you personally completed the user's request.
"""

                try:
                    # Generate response with Bedrock
                    response = await self.llm.ainvoke(
                        [
                            SystemMessage(
                                content="You are a helpful AI assistant providing results to a user."
                            ),
                            HumanMessage(content=response_prompt),
                        ]
                    )
                    final_response = response.content
                except Exception as e:
                    logger.error(f"Response generation with Bedrock failed: {e}")
                    final_response = self._create_fallback_response(state)

            state["final_response"] = final_response

            # Add the final response message
            response_message = AIMessage(content=final_response)
            state["messages"].append(response_message)
            state["step_count"] += 1

            logger.info("Response generation complete")
            return state

        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            fallback_response = self._create_fallback_response(state)

            response_message = AIMessage(content=fallback_response)
            state["messages"].append(response_message)
            state["final_response"] = fallback_response
            state["step_count"] += 1

            return state

    async def _error_recovery_node(self, state: AgentState) -> AgentState:
        """Handle errors and attempt recovery"""
        try:
            original_request = state["messages"][0].content
            tool_results = state.get("tool_results", [])

            error_analysis = "I encountered some issues while processing your request, but let me provide what information I can."

            # Check what tools succeeded and failed
            successful_tools = [r for r in tool_results if r.success]
            failed_tools = [r for r in tool_results if not r.success]

            if successful_tools:
                error_analysis += (
                    f"\n\nI successfully completed {len(successful_tools)} operations:"
                )
                for result in successful_tools:
                    summary = self._summarize_result(result)
                    error_analysis += f"\n• {result.tool_name}: {summary}"

            if failed_tools:
                error_analysis += (
                    f"\n\n{len(failed_tools)} operations encountered issues:"
                )
                for result in failed_tools:
                    error_analysis += (
                        f"\n• {result.tool_name}: {result.error or 'Unknown error'}"
                    )

            if not tool_results:
                error_analysis += f"\n\nRegarding your request: '{original_request}'\n\nI can provide general information and guidance based on my knowledge, even though I couldn't use external tools. What specific aspect would you like me to help with?"
            else:
                error_analysis += "\n\nPlease let me know if you'd like me to retry any specific operations or if you need help with something else."

            state["final_response"] = error_analysis
            error_message = AIMessage(content=error_analysis)
            state["messages"].append(error_message)
            state["step_count"] += 1

            logger.info("Error recovery completed")
            return state

        except Exception as e:
            logger.error(f"Error recovery failed: {str(e)}")
            fallback_message = AIMessage(
                content="I encountered multiple errors while processing your request. Please try rephrasing your request or asking for something simpler that I can help with."
            )
            state["messages"].append(fallback_message)
            state["final_response"] = fallback_message.content
            state["step_count"] += 1
            return state

    def _should_continue_execution(self, state: AgentState) -> str:
        """Determine next step in workflow"""
        # Check if we've exceeded max steps
        if state["step_count"] >= state["max_steps"]:
            logger.info("Max steps reached, proceeding to response")
            return "respond"

        # If no tools were selected, go to response
        if not state.get("selected_tools"):
            logger.info("No tools selected, proceeding to response")
            return "respond"

        # If tools haven't been executed yet, continue
        if not state.get("tool_results"):
            logger.info("Tools not executed yet, continuing")
            return "continue"

        # Check if there were critical failures
        tool_results = state.get("tool_results", [])
        critical_failures = []

        for result in tool_results:
            if not result.success:
                # Check if this was marked as critical in the original tool spec
                for tool_spec in state.get("selected_tools", []):
                    if tool_spec["tool"] == result.tool_name and tool_spec.get(
                        "critical", False
                    ):
                        critical_failures.append(result)
                        break

        if critical_failures:
            logger.info(
                f"Critical failures detected: {[r.tool_name for r in critical_failures]}"
            )
            return "error"

        # All good, generate response
        logger.info("Tool execution completed successfully, proceeding to response")
        return "respond"

    def _summarize_result(self, result: MCPToolResult) -> str:
        """Create a brief summary of a tool result"""
        if not result.success:
            return f"Failed - {result.error}"

        if hasattr(result, "result") and result.result:
            if "message" in result.result:
                return result.result["message"]
            elif "results" in result.result:
                count = len(result.result["results"])
                return f"Found {count} items"
            elif "content" in result.result:
                return f"Retrieved content ({len(result.result['content'])} characters)"
            elif "output" in result.result:
                return "Code executed successfully"

        return "Completed successfully"

    async def process_request(
        self, user_request: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main method to process a user request

        Args:
            user_request: The user's request string
            context: Optional context information

        Returns:
            Dict containing the complete execution results
        """
        try:
            # Set up initial state
            initial_state = {
                "messages": [HumanMessage(content=user_request)],
                "current_task": "",
                "selected_tools": [],
                "tool_results": [],
                "context": context
                or {"session_id": f"session_{int(datetime.now().timestamp())}"},
                "step_count": 0,
                "max_steps": self.max_steps,
                "final_response": "",
            }

            # Use AsyncSqliteSaver as an async context manager
            async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
                # Compile the workflow with checkpointing
                app = self.workflow.compile(checkpointer=checkpointer)

                # Execute the workflow
                config = {
                    "configurable": {
                        "thread_id": f"thread_{int(datetime.now().timestamp())}"
                    }
                }
                final_state = initial_state

                async for chunk in app.astream(initial_state, config):
                    for node_name, node_output in chunk.items():
                        logger.info(f"Completed node: {node_name}")
                        final_state = node_output

            # Clean up MCP connection
            try:
                if hasattr(self.mcp_client, "is_connected"):
                    connected = self.mcp_client.is_connected()
                    if asyncio.iscoroutine(connected):
                        connected = await connected
                    if connected:
                        await self.mcp_client.disconnect()
            except Exception as e:
                logger.warning(f"Error during MCP disconnect: {e}")

            # Return successful result
            return {
                "success": True,
                "final_response": final_state.get(
                    "final_response", "Request processed successfully"
                ),
                "messages": final_state.get("messages", []),
                "tool_results": final_state.get("tool_results", []),
                "steps_taken": final_state.get("step_count", 0),
            }

        except Exception as e:
            logger.error(f"Error occurred while processing request: {e}")
            return {
                "success": False,
                "error": str(e),
                "final_response": f"I encountered an error while processing your request: {str(e)}",
                "messages": [],
                "tool_results": [],
                "steps_taken": 0,
            }


async def interactive_mode():
    """Interactive mode for testing the agent"""
    print("Interactive Bedrock MCP Agent")
    print("Type 'exit' to quit, 'help' for commands")
    print("=" * 50)

    # Create agent
    try:
        agent = BedrockMCPAgent()
        print("Agent ready!")
    except Exception as e:
        print(f"Failed to initialize agent: {str(e)}")
        return

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break

            if user_input.lower() == "help":
                print("\nAvailable commands:")
                print("- exit/quit/q: Exit the program")
                print("- help: Show this help message")
                print("- Any other text: Send request to the agent")
                print("\nExample requests:")
                print("- 'Search for recent AI news and save to a file'")
                print("- 'List all files in the current directory'")
                print("- 'Query the database for project information'")
                continue

            if not user_input:
                continue

            print("\nAgent: Processing your request...")

            start_time = datetime.now()
            result = await agent.process_request(user_input)
            execution_time = (datetime.now() - start_time).total_seconds()

            if result["success"]:
                print(f"\nRequest completed ({execution_time:.2f}s)")
                print("\n" + result["final_response"])

                # Show execution details
                if result["tool_results"]:
                    print(f"\nTools used: {len(result['tool_results'])}")
                    for tool_result in result["tool_results"]:
                        status = "✅" if tool_result.success else "❌"
                        print(
                            f"  {status} {tool_result.tool_name} ({tool_result.execution_time:.2f}s)"
                        )
            else:
                print(f"\nRequest failed: {result.get('error', 'Unknown error')}")
                print(result.get("final_response", "No response available"))

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            break
        except Exception as e:
            print(f"\nError: {str(e)}")


async def main():
    """Main function - choose mode"""
    import sys

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        print("Bedrock MCP Agent")
        print("Choose a mode:")
        print("1. interactive - Interactive chat mode")
        mode = input("Enter mode (1-3): ").strip()

        mode_map = {"1": "interactive"}
        mode = mode_map.get(mode, mode)

    try:
        if mode == "interactive":
            await interactive_mode()

        else:
            print(f"Unknown mode: {mode}")
            print("Available modes: demo, interactive, benchmark")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Main execution error: {str(e)}")
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    # Ensure event loop compatibility
    if os.name == "nt":  # Windows
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    print("Starting Bedrock MCP Agent")
    print("Make sure:")
    print("1. AWS credentials are configured")
    print("2. MCP server is running (python server.py)")
    print("3. Required packages are installed")
    print("=" * 50)

    asyncio.run(main())
