"""Functions/tools package for the AI agent."""

from .read_file_tool import read_file_tool
from .write_file_tool import write_file_tool
from .list_directory_tool import list_directory_tool
from .execute_python_code import execute_python_code
from .execute_python_file import execute_python_file
from .calculate_expression import calculate_expression


def get_tools():
    """Return a list of all available tools."""
    return [
        read_file_tool,
        write_file_tool,
        list_directory_tool,
        execute_python_code,
        execute_python_file,
        calculate_expression,
    ]


__all__ = [
    'read_file_tool',
    'write_file_tool',
    'list_directory_tool',
    'execute_python_code',
    'execute_python_file',
    'calculate_expression',
    'get_tools',
]
