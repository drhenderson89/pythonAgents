"""Tool for executing Python code."""

import os
import sys
from io import StringIO
from langchain_core.tools import tool
from .path_sandbox import get_workdir


@tool
def execute_python_code(code: str) -> str:
    """
    Execute Python code and return the output. Use this for calculations, data processing, or running Python functions.

    Args:
        code: The Python code to execute

    Returns:
        The output of the code execution (stdout), or an error message if execution fails.

    Warning: Only executes code in a restricted environment. Some operations may not be available.
    """
    old_cwd = os.getcwd()
    old_stdout = sys.stdout
    try:
        # Run code from sandbox root so relative file operations stay isolated.
        os.chdir(get_workdir())

        # Capture stdout
        sys.stdout = captured_output = StringIO()

        # Create a restricted execution environment
        exec_globals = {
            '__builtins__': __builtins__,
            'print': print,
            'range': range,
            'len': len,
            'sum': sum,
            'max': max,
            'min': min,
            'abs': abs,
            'round': round,
            'sorted': sorted,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
        }
        exec_locals = {}

        # Execute the code
        exec(code, exec_globals, exec_locals)

        # Restore stdout
        sys.stdout = old_stdout

        # Get the output
        output = captured_output.getvalue()

        if not output:
            # If no print statements, expose the last assigned local value when available.
            if exec_locals:
                last_value = list(exec_locals.values())[-1]
                output = str(last_value)
            else:
                output = "Code executed successfully (no output)."

        return f"Execution output:\n{output}"
    except Exception as e:
        sys.stdout = old_stdout
        return f"Error executing Python code: {str(e)}"
    finally:
        os.chdir(old_cwd)
