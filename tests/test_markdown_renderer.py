"""Tests for markdown_renderer module."""

from ReMD.markdown_renderer import render_markdown
from ReMD.models import FileEntry


class TestRenderMarkdown:
    def test_basic_output_structure(self):
        files = [
            FileEntry(path="README.md", size=11, content="# Hello"),
        ]
        result = render_markdown("owner/repo", files)
        assert "# Repository: owner/repo" in result
        assert "## File Structure" in result
        assert "## Files" in result
        assert "### `README.md`" in result
        assert "# Hello" in result

    def test_file_structure_tree_included(self):
        files = [
            FileEntry(path="src/main.py", size=5, content="x = 1"),
            FileEntry(path="README.md", size=7, content="# Hi"),
        ]
        result = render_markdown("owner/repo", files)
        # Tree should list the text files
        assert "README.md" in result
        assert "main.py" in result

    def test_binary_files_excluded(self):
        files = [
            FileEntry(path="main.py", size=5, content="x = 1"),
            FileEntry(path="logo.png", size=5000, is_binary=True, content=None),
        ]
        result = render_markdown("owner/repo", files)
        assert "### `main.py`" in result
        assert "logo.png" not in result

    def test_files_with_no_content_excluded(self):
        files = [
            FileEntry(path="main.py", size=5, content="x = 1"),
            FileEntry(path="skipped.py", size=5, content=None),
        ]
        result = render_markdown("owner/repo", files)
        assert "### `main.py`" in result
        assert "skipped.py" not in result

    def test_language_hint_from_entry(self):
        files = [
            FileEntry(path="main.py", size=5, content="x = 1", language_hint="python"),
        ]
        result = render_markdown("owner/repo", files)
        assert "```python" in result

    def test_language_hint_fallback(self):
        """When language_hint is empty, get_language_hint should be called."""
        files = [
            FileEntry(path="main.py", size=5, content="x = 1", language_hint=""),
        ]
        result = render_markdown("owner/repo", files)
        # get_language_hint("main.py") returns "python"
        assert "```python" in result

    def test_empty_file_list(self):
        result = render_markdown("owner/repo", [])
        assert "# Repository: owner/repo" in result
        assert "## File Structure" in result
        assert "## Files" in result

    def test_multiple_files_ordered(self):
        files = [
            FileEntry(path="a.py", size=3, content="a"),
            FileEntry(path="b.js", size=3, content="b"),
            FileEntry(path="c.ts", size=3, content="c"),
        ]
        result = render_markdown("owner/repo", files)
        a_pos = result.index("### `a.py`")
        b_pos = result.index("### `b.js`")
        c_pos = result.index("### `c.ts`")
        assert a_pos < b_pos < c_pos

    def test_code_blocks_closed(self):
        files = [
            FileEntry(path="main.py", size=10, content="print('hi')"),
        ]
        result = render_markdown("owner/repo", files)
        # Each code block should be properly opened and closed
        lines = result.split("\n")
        backtick_lines = [l for l in lines if l.startswith("```")]
        # At least: structure open, structure close, file open, file close
        assert len(backtick_lines) >= 4

    def test_empty_content_rendered(self):
        """A file with empty string content should still appear."""
        files = [
            FileEntry(path="empty.py", size=0, content=""),
        ]
        result = render_markdown("owner/repo", files)
        # content="" is not None, so it should be included
        assert "### `empty.py`" in result
