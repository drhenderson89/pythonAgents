"""Tool for writing files to the working directory."""

from langchain_core.tools import tool
from .path_sandbox import resolve_in_workdir, to_relative_display


@tool
def write_file_tool(filename: str, content: str) -> str:
    """
    Write content to a file in the working directory. Creates the file if it doesn't exist.

    Args:
        filename: The name of the file to write (can include subdirectories)
        content: The content to write to the file

    Returns:
        A success message or an error message if the file cannot be written.
    """
    try:
        file_path = resolve_in_workdir(filename)

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"Successfully wrote {len(content)} characters to '{to_relative_display(file_path)}'."
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error writing file '{filename}': {str(e)}"
