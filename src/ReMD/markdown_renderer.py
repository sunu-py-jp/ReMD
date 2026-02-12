"""Markdown output assembly."""

from __future__ import annotations

from ReMD.models import FileEntry
from ReMD.tree_builder import build_tree
from ReMD.file_filter import get_language_hint


def render_markdown(
    repo_display_name: str,
    files: list[FileEntry],
) -> str:
    """Render the repository contents as a single Markdown document.

    Args:
        repo_display_name: e.g. "owner/repo"
        files: list of FileEntry objects with content populated
    """
    parts: list[str] = []

    # Header
    parts.append(f"# Repository: {repo_display_name}\n")

    # File structure
    text_files = [f for f in files if not f.is_binary and f.content is not None]
    all_paths = [f.path for f in text_files]

    parts.append("## File Structure\n")
    parts.append("```")
    parts.append(build_tree(all_paths))
    parts.append("```\n")

    # File contents
    parts.append("## Files\n")

    for entry in text_files:
        lang = entry.language_hint or get_language_hint(entry.path)
        parts.append(f"### `{entry.path}`\n")
        parts.append(f"```{lang}")
        parts.append(entry.content or "")
        parts.append("```\n")

    return "\n".join(parts)
