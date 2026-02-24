TOOL_LIKELY_KEYWORDS = (
    "list",
    "directory",
    "file",
    "read",
    "write",
    "save",
    "edit",
    "create",
    "python",
    "execute",
    "run",
    "calculate",
    "sum",
    "multiply",
    "divide",
)


def prompt_likely_requires_tools(prompt: str) -> bool:
    """Return True when the prompt likely requires a tool call."""
    lowered = prompt.lower()
    return any(keyword in lowered for keyword in TOOL_LIKELY_KEYWORDS)


def build_system_prompt(base_prompt: str, max_iterations: int, enforce_single_tool_step: bool = True) -> str:
    """Append execution-policy instructions to the base system prompt."""
    policy_lines = [
        "You can call tools to interact with the filesystem and execute Python.",
        f"Keep working until the task is complete or the loop reaches {max_iterations} iterations.",
        "If a tool fails, revise arguments and retry when appropriate.",
        "Before finalizing, verify required file operations have been completed.",
    ]

    if enforce_single_tool_step:
        policy_lines.append(
            "Call at most one tool per assistant response. Wait for the tool result before deciding next action."
        )

    return f"{base_prompt}\n\nExecution policy:\n- " + "\n- ".join(policy_lines)
