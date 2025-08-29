from typing import Dict, Any
import json


def _format_parameters_for_tool(
    tool_name: str, parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Format parameters correctly for each tool type"""

    # Map of tool names to their expected parameter structure
    tool_param_mapping = {
        "filesystem": {
            "operation": parameters.get("operation"),
            "path": parameters.get("path"),
            "content": parameters.get("content"),
        },
        "database": {
            "query": parameters.get("query"),
            "database": parameters.get("database", "main"),
        },
        "api_client": {
            "url": parameters.get("url"),
            "method": parameters.get("method", "GET"),
            "headers": parameters.get("headers"),
            "data": parameters.get("data"),
        },
    }

    if tool_name in tool_param_mapping:
        # Remove None values
        formatted = {
            k: v for k, v in tool_param_mapping[tool_name].items() if v is not None
        }
        return formatted

    # Fallback to original parameters
    return parameters


def _parse_tool_result(result) -> Dict[str, Any]:
    """Parse the result from MCP tool call"""
    try:
        if hasattr(result, "content") and result.content:
            content_items = (
                result.content if isinstance(result.content, list) else [result.content]
            )

            parsed_content = []
            for item in content_items:
                if hasattr(item, "text"):
                    text = item.text
                    # Try to parse as JSON
                    if text.strip().startswith(("{", "[")):
                        try:
                            parsed_content.append(json.loads(text))
                        except json.JSONDecodeError:
                            parsed_content.append({"output": text})
                    else:
                        parsed_content.append({"output": text})
                else:
                    parsed_content.append({"content": str(item)})

            if len(parsed_content) == 1:
                return parsed_content[0]
            else:
                return {"results": parsed_content}

        elif hasattr(result, "isError") and result.isError:
            return {"success": False, "error": str(result)}
        else:
            return {"output": "No content returned"}

    except Exception as e:
        return {"output": str(result), "parse_error": str(e)}
