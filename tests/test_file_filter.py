"""Tests for file_filter module."""

from ReMD.file_filter import (
    compile_patterns,
    get_language_hint,
    is_binary_by_content,
    is_binary_by_extension,
    matches_any_pattern,
    parse_pattern_input,
    validate_patterns,
)


class TestIsBinaryByExtension:
    def test_binary_extensions(self):
        assert is_binary_by_extension("image.png") is True
        assert is_binary_by_extension("app.exe") is True
        assert is_binary_by_extension("archive.zip") is True
        assert is_binary_by_extension("data.pdf") is True

    def test_text_extensions(self):
        assert is_binary_by_extension("main.py") is False
        assert is_binary_by_extension("index.js") is False
        assert is_binary_by_extension("README.md") is False

    def test_no_extension(self):
        assert is_binary_by_extension("Makefile") is False
        assert is_binary_by_extension("LICENSE") is False

    def test_case_insensitive(self):
        assert is_binary_by_extension("image.PNG") is True
        assert is_binary_by_extension("photo.JPG") is True

    def test_nested_path(self):
        assert is_binary_by_extension("src/assets/logo.png") is True
        assert is_binary_by_extension("src/main.py") is False


class TestIsBinaryByContent:
    def test_text_content(self):
        assert is_binary_by_content(b"Hello, world!\n") is False

    def test_binary_content(self):
        assert is_binary_by_content(b"\x89PNG\r\n\x1a\n\x00") is True

    def test_null_beyond_8kb(self):
        # Null byte at position 8193 should not be detected
        data = b"a" * 8192 + b"\x00"
        assert is_binary_by_content(data) is False

    def test_empty(self):
        assert is_binary_by_content(b"") is False


class TestGetLanguageHint:
    def test_common_extensions(self):
        assert get_language_hint("main.py") == "python"
        assert get_language_hint("index.js") == "javascript"
        assert get_language_hint("App.tsx") == "tsx"
        assert get_language_hint("style.css") == "css"

    def test_special_filenames(self):
        assert get_language_hint("Dockerfile") == "dockerfile"
        assert get_language_hint("Makefile") == "makefile"
        assert get_language_hint("Gemfile") == "ruby"

    def test_nested_path(self):
        assert get_language_hint("src/utils/helper.ts") == "typescript"
        assert get_language_hint("docker/Dockerfile") == "dockerfile"

    def test_no_extension(self):
        assert get_language_hint("LICENSE") == ""

    def test_unknown_extension(self):
        assert get_language_hint("data.xyz") == ""


class TestParsePatternInput:
    def test_empty_string(self):
        assert parse_pattern_input("") == []

    def test_whitespace_only(self):
        assert parse_pattern_input("   ") == []

    def test_single_pattern(self):
        assert parse_pattern_input(r"\.py$") == [r"\.py$"]

    def test_multiple_patterns(self):
        result = parse_pattern_input(r"\.py$, \.js$, \.ts$")
        assert result == [r"\.py$", r"\.js$", r"\.ts$"]

    def test_strips_whitespace(self):
        result = parse_pattern_input(r"  \.py$  ,  \.js$  ")
        assert result == [r"\.py$", r"\.js$"]

    def test_ignores_empty_segments(self):
        result = parse_pattern_input(r"\.py$,,\.js$,")
        assert result == [r"\.py$", r"\.js$"]


class TestValidatePatterns:
    def test_valid_patterns(self):
        assert validate_patterns([r"\.py$", r"src/.*\.js$"]) == []

    def test_invalid_pattern(self):
        errors = validate_patterns([r"[invalid", r"\.py$"])
        assert len(errors) == 1
        assert "`[invalid`" in errors[0]

    def test_all_invalid(self):
        errors = validate_patterns([r"[bad", r"(unclosed"])
        assert len(errors) == 2

    def test_empty_list(self):
        assert validate_patterns([]) == []


class TestCompilePatterns:
    def test_compiles_valid(self):
        compiled = compile_patterns([r"\.py$", r"\.js$"])
        assert len(compiled) == 2

    def test_skips_invalid(self):
        compiled = compile_patterns([r"\.py$", r"[bad", r"\.js$"])
        assert len(compiled) == 2

    def test_empty(self):
        assert compile_patterns([]) == []


class TestMatchesAnyPattern:
    def test_matches(self):
        compiled = compile_patterns([r"\.py$", r"\.js$"])
        assert matches_any_pattern("src/main.py", compiled) is True
        assert matches_any_pattern("lib/index.js", compiled) is True

    def test_no_match(self):
        compiled = compile_patterns([r"\.py$"])
        assert matches_any_pattern("style.css", compiled) is False

    def test_empty_patterns_matches_all(self):
        assert matches_any_pattern("anything.txt", []) is True

    def test_partial_match(self):
        compiled = compile_patterns([r"src/"])
        assert matches_any_pattern("src/main.py", compiled) is True
        assert matches_any_pattern("lib/main.py", compiled) is False

    def test_complex_pattern(self):
        compiled = compile_patterns([r"src/.*\.(ts|tsx)$"])
        assert matches_any_pattern("src/App.tsx", compiled) is True
        assert matches_any_pattern("src/utils/helper.ts", compiled) is True
        assert matches_any_pattern("src/style.css", compiled) is False
        assert matches_any_pattern("lib/App.tsx", compiled) is False
