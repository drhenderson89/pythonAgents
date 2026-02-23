"""Tool for reading files from the working directory."""

from pathlib import Path
from langchain_core.tools import tool
from .path_sandbox import get_workdir, resolve_in_workdir, to_relative_display


@tool
def read_file_tool(filename: str) -> str:
    """
    Read a file from the working directory.

    Args:
        filename: The name of the file to read (can include subdirectories)

    Returns:
        The contents of the file as a string, or an error message if the file cannot be read.
    """
    try:
        file_path = resolve_in_workdir(filename)

        if not file_path.exists():
            # Fallback: try resolving by filename stem (e.g. "test_text" -> "test_text.txt")
            requested = Path(filename)
            requested_parent = requested.parent if str(
                requested.parent) != "." else None
            requested_name = requested.name

            workdir = get_workdir()
            stem_matches = []
            for candidate in workdir.rglob("*"):
                if not candidate.is_file():
                    continue
                rel_candidate = candidate.relative_to(workdir)

                if requested_parent and rel_candidate.parent != requested_parent:
                    continue

                if rel_candidate.name == requested_name or rel_candidate.stem == requested_name:
                    stem_matches.append(candidate)

            if len(stem_matches) == 1:
                file_path = stem_matches[0]
            elif len(stem_matches) > 1:
                options = "\n".join(
                    f"- {to_relative_display(path)}" for path in stem_matches[:10])
                return (
                    f"Error: Multiple files match '{filename}'. Please specify one of:\n{options}"
                )
            else:
                return f"Error: File '{filename}' not found in working directory."

        if not file_path.is_file():
            return f"Error: '{filename}' is not a file."

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return f"Content of '{to_relative_display(file_path)}':\n{content}"
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error reading file '{filename}': {str(e)}"
