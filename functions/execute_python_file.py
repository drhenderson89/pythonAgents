"""Tool for executing Python files from the working directory."""

import sys
import subprocess
from langchain_core.tools import tool
from .path_sandbox import get_workdir, resolve_in_workdir


@tool
def execute_python_file(filepath: str, arguments: str) -> str:
    """
    Execute a Python file from the working directory or a subdirectory.

    Args:
        filepath: The path to the Python file to execute (relative to working directory)
        arguments: Command-line arguments to pass to the script (use empty string "" if none needed)

    Returns:
        The output (stdout and stderr) from executing the Python file, or an error message.

    Example:
        execute_python_file("script.py", "--verbose --count 10")
        execute_python_file("calculator/tests.py", "")
    """
    try:
        file_path = resolve_in_workdir(filepath)

        if not file_path.exists():
            return f"Error: Python file '{filepath}' not found in working directory."

        if not file_path.is_file():
            return f"Error: '{filepath}' is not a file."

        if file_path.suffix != '.py':
            return f"Error: '{filepath}' is not a Python file (.py extension required)."

        # Build command
        cmd = [sys.executable, str(file_path)]
        if arguments:
            # Split args but respect quoted strings
            import shlex
            cmd.extend(shlex.split(arguments))

        # Execute the Python file
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,  # 30 second timeout to prevent infinite loops
            cwd=get_workdir()
        )

        # Combine stdout and stderr
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"

        if result.returncode != 0:
            output += f"\nProcess exited with code {result.returncode}"
        elif not output:
            output = "Script executed successfully (no output)."

        return output.strip()

    except subprocess.TimeoutExpired:
        return f"Error: Execution of '{filepath}' timed out after 30 seconds."
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error executing Python file '{filepath}': {str(e)}"
