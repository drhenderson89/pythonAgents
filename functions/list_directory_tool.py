"""Tool for listing directory contents."""

from langchain_core.tools import tool
from .path_sandbox import resolve_in_workdir, to_relative_display


@tool
def list_directory_tool(path: str = ".") -> str:
    """
    List files and directories in the working directory or a subdirectory.

    Args:
        path: The directory path to list (default is current directory)

    Returns:
        A formatted list of files and directories, or an error message.
    """
    try:
        dir_path = resolve_in_workdir(path)

        if not dir_path.exists():
            return f"Error: Directory '{path}' not found."

        if not dir_path.is_dir():
            return f"Error: '{path}' is not a directory."

        items = []
        for item in sorted(dir_path.iterdir()):
            if item.is_dir():
                items.append(f"[DIR]  {item.name}/")
            else:
                size = item.stat().st_size
                items.append(f"[FILE] {item.name} ({size} bytes)")

        if not items:
            return f"Directory '{path}' is empty."

        return f"Contents of '{to_relative_display(dir_path)}':\n" + "\n".join(items)
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error listing directory '{path}': {str(e)}"
