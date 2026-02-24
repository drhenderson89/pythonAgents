import json
from typing import Any, Dict, List, Tuple

from langchain_core.messages import HumanMessage


def safe_preview(value: str, limit: int = 200) -> str:
    """Return a truncated preview string suitable for logs and traces."""
    # Keep logs and traces compact while preserving enough context to debug failures.
    return value if len(value) <= limit else f"{value[:limit]}..."


def append_tool_trace(
    tool_trace: List[Dict[str, Any]],
    iteration: int,
    tool_name: str,
    args: Dict[str, Any],
    result: str,
    status: str,
) -> None:
    """Append a normalized tool invocation entry to the tool trace list."""
    # Store normalized tool activity for UI/debug reporting and loop decisions.
    tool_trace.append(
        {
            "iteration": iteration,
            "tool": tool_name,
            "args": args,
            "status": status,
            "result": result,
            "result_preview": safe_preview(result, limit=400),
        }
    )


def has_successful_tool_call(tool_trace: List[Dict[str, Any]], tool_names: tuple[str, ...]) -> bool:
    """Return True if any named tool has at least one successful trace entry."""
    # Used by guardrails that depend on whether a specific capability already succeeded.
    return any(
        entry.get("status") == "success" and entry.get("tool") in tool_names
        for entry in tool_trace
    )


def latest_user_prompt(messages: List[Any]) -> str:
    """Return the newest HumanMessage content from a message history."""
    # Read latest human instruction to infer policy nudges (for example Python execution intent).
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def has_repeated_identical_error(
    tool_trace: List[Dict[str, Any]],
    tool_name: str,
    tool_args: Dict[str, Any],
    repeat_count: int = 3,
) -> bool:
    """Detect repeated consecutive errors for the same tool call arguments."""
    # Detect repeated identical failures (same tool + same args) in the recent
    # consecutive error window so the loop can force a strategy change.
    normalized_args = json.dumps(tool_args or {}, sort_keys=True, default=str)
    matched = 0

    for entry in reversed(tool_trace):
        if entry.get("status") != "error":
            break
        if entry.get("tool") != tool_name:
            break

        entry_args = json.dumps(entry.get("args") or {}, sort_keys=True, default=str)
        if entry_args != normalized_args:
            break

        matched += 1
        if matched >= repeat_count:
            return True

    return False


def execute_tool_call(tool_call: Dict[str, Any], tool_map: Dict[str, Any]) -> Tuple[str, str]:
    """Invoke a mapped tool call and classify the result as success or error."""
    # Centralized tool dispatch so status classification is consistent for all tools.
    tool_name = tool_call.get("name")
    tool_args = tool_call.get("args", {})

    if tool_name not in tool_map:
        return f"Error: Tool {tool_name} not found", "error"

    try:
        tool = tool_map[tool_name]
        result = tool.invoke(tool_args)
        result_text = str(result)
        status = "error" if result_text.strip().lower().startswith("error") else "success"
        return result_text, status
    except Exception as error:
        return f"Error executing {tool_name}: {error}", "error"
