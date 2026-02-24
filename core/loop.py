import json
from typing import Any, Callable, Dict, List

from langchain_core.messages import HumanMessage, ToolMessage

from .logging_utils import RUNTIME_LOGGER
from .tool_utils import (
    append_tool_trace,
    execute_tool_call,
    has_repeated_identical_error,
    has_successful_tool_call,
    latest_user_prompt,
    safe_preview,
)


def _emit_tool_event(
    on_tool_event: Callable[[Dict[str, Any]], None] | None,
    iteration: int,
    tool_name: str,
    tool_args: Dict[str, Any],
    status: str,
    result_preview: str,
    skipped: bool,
) -> None:
    """Emit a normalized callback event for a processed tool call."""
    if not on_tool_event:
        return

    on_tool_event(
        {
            "iteration": iteration,
            "tool": tool_name,
            "args": tool_args,
            "status": status,
            "result_preview": result_preview,
            "skipped": skipped,
        }
    )


def _record_skipped_tool_calls(
    tool_calls: List[Dict[str, Any]],
    iteration: int,
    run_label: str,
    tool_trace: List[Dict[str, Any]],
    messages: List[Any],
    on_tool_event: Callable[[Dict[str, Any]], None] | None,
) -> int:
    """Record and message extra tool calls skipped by single-tool policy."""
    # Enforce single-tool-per-turn policy by recording any additional tool calls
    # as skipped ToolMessages. This keeps model state consistent and auditable.
    skipped_count = 0
    for skipped_index, skipped_call in enumerate(tool_calls[1:], start=1):
        skipped_name = skipped_call.get("name", "unknown")
        skipped_args = skipped_call.get("args", {})
        skipped_tool_call_id = skipped_call.get("id") or f"generated-{iteration}-{skipped_index}"
        skipped_result = "Skipped: only one tool call is allowed per assistant turn. Retry this tool in a later turn if needed."

        skipped_count += 1
        RUNTIME_LOGGER.warning(
            "tool_call_skipped label=%s iteration=%s tool=%s",
            run_label,
            iteration,
            skipped_name,
        )
        append_tool_trace(
            tool_trace, iteration, skipped_name, skipped_args, skipped_result, "skipped"
        )
        messages.append(ToolMessage(content=skipped_result, tool_call_id=skipped_tool_call_id))

        _emit_tool_event(
            on_tool_event=on_tool_event,
            iteration=iteration,
            tool_name=skipped_name,
            tool_args=skipped_args,
            status="skipped",
            result_preview=safe_preview(skipped_result),
            skipped=True,
        )

    return skipped_count


def _append_tool_error_guidance(
    messages: List[Any],
    tool_trace: List[Dict[str, Any]],
    tool_name: str,
    tool_args: Dict[str, Any],
    result: str,
    prompt_requires_python_execution: bool,
    run_label: str,
    iteration: int,
) -> None:
    """Append recovery guidance messages after a failed tool invocation."""
    # Add progressive guidance messages after tool failures so the model retries
    # with better arguments instead of finalizing prematurely.
    RUNTIME_LOGGER.warning(
        "tool_call_retry_hint label=%s iteration=%s tool=%s",
        run_label,
        iteration,
        tool_name,
    )
    messages.append(
        HumanMessage(
            content=(
                "The previous tool call failed. Fix the arguments and continue the task. "
                "Do not finish until the required operation succeeds or you have a concrete blocker."
            )
        )
    )

    error_text = result.lower()
    filepath_arg = str(tool_args.get("filepath", "")).strip()
    file_tool_misuse = (
        tool_name == "execute_python_file"
        and (
            not filepath_arg
            or "is not a python file" in error_text
            or "not found" in error_text
            or "is not a file" in error_text
        )
    )

    if prompt_requires_python_execution and file_tool_misuse:
        RUNTIME_LOGGER.warning(
            "execute_python_file_misuse_detected label=%s iteration=%s",
            run_label,
            iteration,
        )
        messages.append(
            HumanMessage(
                content=(
                    "Do not use execute_python_file for this task unless you are running an existing .py script path. "
                    "Use execute_python_code instead. Build one complete Python snippet that opens each file, "
                    "concatenates the contents, prints the result, and then return the tool output."
                )
            )
        )

    if tool_name == "execute_python_code" and (
        "was never closed" in error_text
        or "syntaxerror" in error_text
        or "unexpected eof" in error_text
    ):
        RUNTIME_LOGGER.warning(
            "execute_python_code_incomplete_snippet label=%s iteration=%s",
            run_label,
            iteration,
        )
        messages.append(
            HumanMessage(
                content=(
                    "Your Python snippet was incomplete or invalid. Retry execute_python_code with a full, "
                    "syntactically valid snippet and include print() output."
                )
            )
        )

    if tool_name == "execute_python_code" and (
        "is a directory" in error_text
        or "errno 21" in error_text
    ):
        RUNTIME_LOGGER.warning(
            "execute_python_code_directory_open_error label=%s iteration=%s",
            run_label,
            iteration,
        )
        messages.append(
            HumanMessage(
                content=(
                    "Your Python code attempted to open a directory as a file. "
                    "Retry execute_python_code and only open real files, for example by checking "
                    "os.path.isfile(path) before calling open()."
                )
            )
        )

    if has_repeated_identical_error(tool_trace, tool_name, tool_args):
        RUNTIME_LOGGER.warning(
            "repeated_identical_tool_error label=%s iteration=%s tool=%s",
            run_label,
            iteration,
            tool_name,
        )
        if prompt_requires_python_execution:
            messages.append(
                HumanMessage(
                    content=(
                        "You are repeating the same failing tool call. Stop repeating it. "
                        "Switch to execute_python_code and produce real output now."
                    )
                )
            )
        else:
            messages.append(
                HumanMessage(
                    content=(
                        "You are repeating the same failing tool call with the same arguments. "
                        "Change your approach and call a different, more appropriate tool."
                    )
                )
            )


def _maybe_nudge_after_repeated_list(
    messages: List[Any],
    tool_trace: List[Dict[str, Any]],
    prompt_requires_python_execution: bool,
    python_tool_executed_before_call: bool,
    tool_name: str,
    iteration: int,
    max_iterations: int,
    run_label: str,
) -> None:
    """Nudge toward Python execution after redundant directory listings."""
    # If the model keeps listing directories for an execution task, nudge it
    # toward actually running Python instead of repeating discovery steps.
    if not (
        iteration < max_iterations
        and prompt_requires_python_execution
        and not python_tool_executed_before_call
        and tool_name == "list_directory_tool"
        and has_successful_tool_call(tool_trace, ("list_directory_tool",))
    ):
        return

    RUNTIME_LOGGER.warning(
        "repeated_list_without_python_execution label=%s iteration=%s",
        run_label,
        iteration,
    )
    messages.append(
        HumanMessage(
            content=(
                "Directory listing is already available. Next, call execute_python_code to open all files "
                "in the working directory, concatenate their contents, print the result, and return that output. "
                "Only open file paths (skip directories) by checking os.path.isfile(path) first. "
                "Do not call list_directory_tool again unless the directory changed."
            )
        )
    )


def _should_retry_without_tools(
    likely_requires_tools: bool,
    successful_tool_calls: int,
    no_tool_response_turns: int,
    iteration: int,
    max_iterations: int,
) -> bool:
    """Return True when a no-tool response should trigger a retry nudge."""
    # Allow one corrective nudge when a tool-capable task receives a plain-text response.
    return (
        likely_requires_tools
        and successful_tool_calls == 0
        and no_tool_response_turns == 1
        and iteration < max_iterations
    )


def _should_force_python_execution(
    iteration: int,
    max_iterations: int,
    prompt_requires_python_execution: bool,
    python_tool_executed: bool,
    response_content: str,
) -> bool:
    """Return True when completion should be blocked until Python is executed."""
    # Detect likely "pseudo-code" answers for Python-required prompts and force
    # a real tool execution before completion.
    response_has_code_block = "```" in response_content
    return (
        iteration < max_iterations
        and prompt_requires_python_execution
        and not python_tool_executed
        and (
            response_has_code_block
            or "we will use python" in response_content.lower()
            or "execution output" not in response_content.lower()
        )
    )


def _python_execution_escalation_message(no_tool_response_turns: int) -> str:
    """Build escalating instructions that force a Python execution tool call."""
    # Escalate instructions after repeated non-tool responses.
    if no_tool_response_turns < 3:
        return (
            "Do not stop at pseudo-code. Execute Python now using the available tool "
            "and provide the actual output."
        )

    return (
        "Your next response must be exactly one tool call to execute_python_code and no plain text. Generate a complete, syntactically"
        " valid Python snippet that solves the user’s requested task, includes any required imports, handles obvious edge cases, and prints the"
        " final result. Do not repeat prior failing code. After the tool returns, use that output to continue."
        #"Your next response must be a single tool call to execute_python_code and no plain text. "
        #"Use code equivalent to:\n"
        #"import os\n"
        #"parts = []\n"
        #"for name in sorted(os.listdir('.')):\n"
        #"    path = os.path.join('.', name)\n"
        #"    if os.path.isfile(path):\n"
        #"        with open(path, 'r', encoding='utf-8', errors='replace') as f:\n"
        #"            parts.append(f.read())\n"
        #"print(''.join(parts))\n"
        #"Then wait for the tool result."
    )


def _should_abort_for_tool_refusal(
    likely_requires_tools: bool,
    prompt_requires_python_execution: bool,
    successful_tool_calls: int,
    no_tool_response_turns: int,
    refusal_threshold: int = 6,
) -> bool:
    """Return True when repeated tool refusal should end the run."""
    # Stop early when the model repeatedly refuses tool usage for an execution-required task.
    return (
        likely_requires_tools
        and prompt_requires_python_execution
        and successful_tool_calls == 0
        and no_tool_response_turns >= refusal_threshold
    )


def _has_unresolved_tool_error(tool_trace: List[Dict[str, Any]]) -> bool:
    """Return True when the latest tool status is an error without later success."""
    # A final response is not considered safe if the last error happens after
    # the last success in the tool trace.
    last_error_index = -1
    last_success_index = -1
    for index, entry in enumerate(tool_trace):
        status_value = entry.get("status")
        if status_value == "error":
            last_error_index = index
        elif status_value == "success":
            last_success_index = index

    return last_error_index > last_success_index


def run_agent_turns(
    model_with_tools: Any,
    tool_map: Dict[str, Any],
    messages: List[Any],
    max_iterations: int,
    likely_requires_tools: bool = False,
    on_tool_event: Callable[[Dict[str, Any]], None] | None = None,
    run_label: str = "agent",
) -> Dict[str, Any]:
    """Run the model/tool loop with guardrails until completion or stop conditions."""
    # Per-turn run state used for guardrails and termination decisions.
    total_tool_calls = 0
    successful_tool_calls = 0
    no_tool_response_turns = 0
    tool_trace: List[Dict[str, Any]] = []
    initial_user_prompt = latest_user_prompt(messages).lower()
    prompt_requires_python_execution = any(
        keyword in initial_user_prompt
        for keyword in ("use python", "concatenate", "print", "execute", "run python")
    )

    RUNTIME_LOGGER.info(
        "run_start label=%s max_iterations=%s likely_requires_tools=%s",
        run_label,
        max_iterations,
        likely_requires_tools,
    )

    for iteration in range(1, max_iterations + 1):
        try:
            RUNTIME_LOGGER.info(
                "iteration_start label=%s iteration=%s message_count=%s",
                run_label,
                iteration,
                len(messages),
            )

            try:
                response = model_with_tools.invoke(messages)
            except Exception:
                RUNTIME_LOGGER.exception(
                    "iteration_model_invoke_error label=%s iteration=%s",
                    run_label,
                    iteration,
                )
                raise
            messages.append(response)

            tool_calls = response.tool_calls or []
            RUNTIME_LOGGER.info(
                "iteration_model_response label=%s iteration=%s tool_calls=%s",
                run_label,
                iteration,
                len(tool_calls),
            )
            if tool_calls:
                # Process only the first tool call each turn; extras are marked skipped
                # to preserve deterministic tool sequencing.
                no_tool_response_turns = 0
                primary_tool_call = tool_calls[0]
                tool_name = primary_tool_call.get("name", "unknown")
                tool_args = primary_tool_call.get("args", {})
                primary_tool_call_id = primary_tool_call.get("id") or f"generated-{iteration}-0"
                python_tool_executed_before_call = has_successful_tool_call(
                    tool_trace,
                    ("execute_python_code", "execute_python_file"),
                )

                RUNTIME_LOGGER.info(
                    "tool_call_start label=%s iteration=%s tool=%s args=%s",
                    run_label,
                    iteration,
                    tool_name,
                    json.dumps(tool_args, default=str),
                )

                result, status = execute_tool_call(primary_tool_call, tool_map)
                total_tool_calls += 1
                if status == "success":
                    successful_tool_calls += 1

                RUNTIME_LOGGER.info(
                    "tool_call_end label=%s iteration=%s tool=%s status=%s result_preview=%s",
                    run_label,
                    iteration,
                    tool_name,
                    status,
                    safe_preview(result),
                )

                append_tool_trace(tool_trace, iteration, tool_name, tool_args, result, status)
                messages.append(ToolMessage(content=result, tool_call_id=primary_tool_call_id))

                _emit_tool_event(
                    on_tool_event=on_tool_event,
                    iteration=iteration,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    status=status,
                    result_preview=safe_preview(result),
                    skipped=False,
                )

                total_tool_calls += _record_skipped_tool_calls(
                    tool_calls=tool_calls,
                    iteration=iteration,
                    run_label=run_label,
                    tool_trace=tool_trace,
                    messages=messages,
                    on_tool_event=on_tool_event,
                )

                if status == "error" and iteration < max_iterations:
                    # Keep the model in a repair loop rather than ending with a failed step.
                    _append_tool_error_guidance(
                        messages=messages,
                        tool_trace=tool_trace,
                        tool_name=tool_name,
                        tool_args=tool_args,
                        result=result,
                        prompt_requires_python_execution=prompt_requires_python_execution,
                        run_label=run_label,
                        iteration=iteration,
                    )

                _maybe_nudge_after_repeated_list(
                    messages=messages,
                    tool_trace=tool_trace,
                    prompt_requires_python_execution=prompt_requires_python_execution,
                    python_tool_executed_before_call=python_tool_executed_before_call,
                    tool_name=tool_name,
                    iteration=iteration,
                    max_iterations=max_iterations,
                    run_label=run_label,
                )

                continue

            no_tool_response_turns += 1
            response_content = (response.content or "").strip()

            if _should_retry_without_tools(
                likely_requires_tools=likely_requires_tools,
                successful_tool_calls=successful_tool_calls,
                no_tool_response_turns=no_tool_response_turns,
                iteration=iteration,
                max_iterations=max_iterations,
            ):
                RUNTIME_LOGGER.warning(
                    "no_tool_when_expected label=%s iteration=%s",
                    run_label,
                    iteration,
                )
                messages.append(
                    HumanMessage(
                        content=(
                            "You answered without tools, but this task likely requires tool use. "
                            "Use the necessary tool now and then continue."
                        )
                    )
                )
                continue

            python_tool_executed = has_successful_tool_call(
                tool_trace,
                ("execute_python_code", "execute_python_file"),
            )

            if _should_force_python_execution(
                iteration=iteration,
                max_iterations=max_iterations,
                prompt_requires_python_execution=prompt_requires_python_execution,
                python_tool_executed=python_tool_executed,
                response_content=response_content,
            ):
                # Prevent "looks-done" textual answers when actual execution output is required.
                RUNTIME_LOGGER.warning(
                    "python_execution_required_before_finalize label=%s iteration=%s",
                    run_label,
                    iteration,
                )
                if no_tool_response_turns >= 3:
                    RUNTIME_LOGGER.warning(
                        "python_execution_escalated_instruction label=%s iteration=%s no_tool_turns=%s",
                        run_label,
                        iteration,
                        no_tool_response_turns,
                    )
                messages.append(
                    HumanMessage(
                        content=_python_execution_escalation_message(no_tool_response_turns)
                    )
                )

                if _should_abort_for_tool_refusal(
                    likely_requires_tools=likely_requires_tools,
                    prompt_requires_python_execution=prompt_requires_python_execution,
                    successful_tool_calls=successful_tool_calls,
                    no_tool_response_turns=no_tool_response_turns,
                ):
                    RUNTIME_LOGGER.error(
                        "tool_refusal_abort label=%s iteration=%s no_tool_turns=%s",
                        run_label,
                        iteration,
                        no_tool_response_turns,
                    )
                    return {
                        "response": (
                            "The model repeatedly refused to call tools for a task that requires execution. "
                            "Try a tool-calling-capable model or adjust model/tool configuration."
                        ),
                        "iterations": iteration,
                        "tool_calls": total_tool_calls,
                        "completed": False,
                        "stop_reason": "model_refused_tools",
                        "tool_trace": tool_trace,
                    }
                continue

            unresolved_tool_error = _has_unresolved_tool_error(tool_trace)
            if unresolved_tool_error and no_tool_response_turns == 1 and iteration < max_iterations:
                RUNTIME_LOGGER.warning(
                    "prior_tool_error_requires_recheck label=%s iteration=%s",
                    run_label,
                    iteration,
                )
                messages.append(
                    HumanMessage(
                        content=(
                            "There was a prior tool failure. Retry with corrected arguments before finalizing. "
                            "Only finalize if completion is impossible, and explain why."
                        )
                    )
                )
                continue

            if likely_requires_tools and successful_tool_calls == 0:
                RUNTIME_LOGGER.error(
                    "run_complete_without_tools label=%s iterations=%s",
                    run_label,
                    iteration,
                )
                return {
                    "response": (
                        "I could not complete this request because the model did not call any tools. "
                        "Please try a different model or tool-calling configuration."
                    ),
                    "iterations": iteration,
                    "tool_calls": total_tool_calls,
                    "completed": False,
                    "stop_reason": "no_tool_calls",
                    "tool_trace": tool_trace,
                }

            RUNTIME_LOGGER.info(
                "run_complete label=%s iterations=%s tool_calls=%s successful_tool_calls=%s",
                run_label,
                iteration,
                total_tool_calls,
                successful_tool_calls,
            )
            return {
                "response": response_content,
                "iterations": iteration,
                "tool_calls": total_tool_calls,
                "completed": True,
                "stop_reason": "completed",
                "tool_trace": tool_trace,
            }

        except Exception:
            RUNTIME_LOGGER.exception(
                "iteration_runtime_error label=%s iteration=%s",
                run_label,
                iteration,
            )
            return {
                "response": "I hit an internal runtime error while processing your request. Check agent logs for details.",
                "iterations": iteration,
                "tool_calls": total_tool_calls,
                "completed": False,
                "stop_reason": "runtime_error",
                "tool_trace": tool_trace,
            }

    RUNTIME_LOGGER.error(
        "run_max_iterations label=%s iterations=%s tool_calls=%s successful_tool_calls=%s",
        run_label,
        max_iterations,
        total_tool_calls,
        successful_tool_calls,
    )
    return {
        "response": "I reached the maximum iteration limit before completing this request.",
        "iterations": max_iterations,
        "tool_calls": total_tool_calls,
        "completed": False,
        "stop_reason": "max_iterations",
        "tool_trace": tool_trace,
    }
