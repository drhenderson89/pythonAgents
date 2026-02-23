"""Compatibility facade for shared runtime APIs."""

from .logging_utils import RUNTIME_LOGGER, configure_runtime_logger
from .loop import run_agent_turns
from .prompting import build_system_prompt, prompt_likely_requires_tools

__all__ = [
    "RUNTIME_LOGGER",
    "build_system_prompt",
    "configure_runtime_logger",
    "prompt_likely_requires_tools",
    "run_agent_turns",
]
