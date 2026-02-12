"""Tests for tree_builder module."""

from ReMD.tree_builder import build_tree


class TestBuildTree:
    def test_empty(self):
        assert build_tree([]) == ""

    def test_single_file(self):
        result = build_tree(["README.md"])
        assert result == "└── README.md"

    def test_flat_files(self):
        result = build_tree(["LICENSE", "README.md"])
        lines = result.split("\n")
        assert lines[0] == "├── LICENSE"
        assert lines[1] == "└── README.md"

    def test_nested_structure(self):
        paths = [
            "src/main.py",
            "src/utils.py",
            "README.md",
        ]
        result = build_tree(paths)
        lines = result.split("\n")
        # Sorted: README.md comes before src/
        assert "├── README.md" in lines[0]
        assert "└── src/" in lines[1]
        assert "    ├── main.py" in lines[2]
        assert "    └── utils.py" in lines[3]

    def test_deep_nesting(self):
        paths = [
            "a/b/c/d.txt",
        ]
        result = build_tree(paths)
        assert "└── a/" in result
        assert "    └── b/" in result
        assert "        └── c/" in result
        assert "            └── d.txt" in result

    def test_sorted_output(self):
        paths = ["z.txt", "a.txt", "m.txt"]
        result = build_tree(paths)
        lines = result.split("\n")
        assert "a.txt" in lines[0]
        assert "m.txt" in lines[1]
        assert "z.txt" in lines[2]
