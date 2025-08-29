import json
from typing import Dict, Any, List
from client_side.utils.mcp_tools_models import MCPToolResult


def _format_tools_for_prompt(tools) -> str:
    """Format available tools for the analysis prompt"""
    if not tools:
        return "No tools available"

    tools_text = ""
    for tool in tools:
        tools_text += f"\n**{tool.name}**: {tool.description}\n"

        # Add parameter information if available
        if (
            hasattr(tool, "input_schema")
            and tool.input_schema
            and isinstance(tool.input_schema, dict)
        ):
            properties = tool.input_schema.get("properties", {})
            required = tool.input_schema.get("required", [])

            if properties:
                tools_text += "  Parameters:\n"
                for param, schema in properties.items():
                    is_required = param in required
                    param_desc = schema.get(
                        "description", schema.get("type", "parameter")
                    )
                    tools_text += f"    - {param} ({'required' if is_required else 'optional'}): {param_desc}\n"
        tools_text += "\n"

    return tools_text


def _format_results_for_prompt(results: List[MCPToolResult]) -> str:
    """Format tool results for response generation prompt"""
    if not results:
        return "No tool results available"

    results_text = ""

    for result in results:
        status = "SUCCESS" if result.success else "FAILED"
        results_text += (
            f"\n{status} - {result.tool_name} ({result.execution_time:.2f}s)\n"
        )

        if result.success and hasattr(result, "result") and result.result:
            # Handle different result formats
            if isinstance(result.result, dict):
                if "content" in result.result:
                    content = str(result.result["content"])
                    if len(content) > 300:
                        content = content[:300] + "... [truncated]"
                    results_text += f"  Content: {content}\n"

                if "results" in result.result and isinstance(
                    result.result["results"], list
                ):
                    count = len(result.result["results"])
                    results_text += f"  Found {count} results\n"
                    # Include first few results
                    for i, item in enumerate(result.result["results"][:3]):
                        if isinstance(item, dict):
                            title = item.get("title", item.get("name", f"Result {i+1}"))
                            results_text += f"    - {title}\n"

                if "message" in result.result:
                    results_text += f"  Message: {result.result['message']}\n"

                if "output" in result.result:
                    output = str(result.result["output"])
                    if len(output) > 200:
                        output = output[:200] + "... [truncated]"
                    results_text += f"  Output: {output}\n"

                if "files" in result.result:
                    files = result.result["files"]
                    if isinstance(files, list):
                        results_text += f"  Found {len(files)} files\n"
            else:
                results_text += f"  Result: {str(result.result)[:200]}\n"
        else:
            results_text += f"  Error: {result.error or 'Unknown error'}\n"

    return results_text


def _parse_json_response(response_text: str) -> Dict[str, Any]:
    """Parse JSON from LLM response with better error handling"""
    try:
        # Try to find JSON block in the response
        response_text = response_text.strip()

        # Look for JSON block markers
        if "```json" in response_text.lower():
            start_marker = response_text.lower().find("```json") + 7
            end_marker = response_text.find("```", start_marker)
            if end_marker > start_marker:
                json_str = response_text[start_marker:end_marker].strip()
            else:
                json_str = response_text[start_marker:].strip()
        else:
            # Try to find JSON object boundaries
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
            else:
                json_str = response_text

        # Parse JSON
        parsed = json.loads(json_str)

        # Validate required fields
        if not isinstance(parsed, dict):
            raise ValueError("Response is not a JSON object")

        # Ensure required fields exist
        if "selected_tools" not in parsed:
            parsed["selected_tools"] = []
        if "task_analysis" not in parsed:
            parsed["task_analysis"] = "Task analysis not provided"

        return parsed

    except Exception as e:
        return {
            "task_analysis": "Could not parse analysis response",
            "selected_tools": [],
            "execution_plan": "Fallback plan",
            "expected_outcome": "Basic response",
            "error": str(e),
        }
