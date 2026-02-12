"""ASCII tree builder for file structure display."""

from __future__ import annotations


def build_tree(paths: list[str]) -> str:
    """Build an ASCII directory tree from a list of file paths.

    Example output:
        ├── src/
        │   ├── main.py
        │   └── utils.py
        └── README.md
    """
    if not paths:
        return ""

    # Build a nested dict representing the directory structure
    tree: dict = {}
    for path in sorted(paths):
        parts = path.split("/")
        node = tree
        for part in parts:
            node = node.setdefault(part, {})

    lines: list[str] = []
    _render_tree(tree, lines, prefix="")
    return "\n".join(lines)


def _render_tree(
    tree: dict,
    lines: list[str],
    prefix: str,
) -> None:
    """Recursively render the tree into lines."""
    entries = list(tree.items())
    for i, (name, children) in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "

        # Append "/" for directories
        display_name = f"{name}/" if children else name
        lines.append(f"{prefix}{connector}{display_name}")

        if children:
            extension = "    " if is_last else "│   "
            _render_tree(children, lines, prefix + extension)
