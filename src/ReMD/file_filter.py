"""Binary file detection, language hint mapping, and regex path filtering."""

from __future__ import annotations

import re

# Extensions that are definitely binary — skip without downloading
BINARY_EXTENSIONS: frozenset[str] = frozenset({
    # Images
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp", ".tiff",
    # Compiled / executables
    ".exe", ".dll", ".so", ".dylib", ".o", ".obj", ".class", ".pyc", ".pyo",
    # Archives
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar", ".jar", ".war",
    # Media
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".flac", ".ogg", ".mkv", ".webm",
    # Fonts
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    # Documents (binary)
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    # Databases
    ".db", ".sqlite", ".sqlite3",
    # Other
    ".bin", ".dat", ".lock", ".DS_Store",
})

# Mapping of extension → Markdown code-fence language hint
LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "jsx",
    ".tsx": "tsx",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".ps1": "powershell",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".xml": "xml",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "rst",
    ".tex": "latex",
    ".r": "r",
    ".R": "r",
    ".scala": "scala",
    ".lua": "lua",
    ".pl": "perl",
    ".pm": "perl",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".dart": "dart",
    ".vue": "vue",
    ".svelte": "svelte",
    ".tf": "hcl",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".dockerfile": "dockerfile",
    ".makefile": "makefile",
}

# Special filenames that have a known language
FILENAME_LANGUAGE_MAP: dict[str, str] = {
    "Dockerfile": "dockerfile",
    "Makefile": "makefile",
    "Jenkinsfile": "groovy",
    "Vagrantfile": "ruby",
    "Gemfile": "ruby",
    "Rakefile": "ruby",
    "CMakeLists.txt": "cmake",
    ".gitignore": "gitignore",
    ".dockerignore": "gitignore",
    ".editorconfig": "ini",
}


def is_binary_by_extension(path: str) -> bool:
    """Check if a file is likely binary based on its extension."""
    dot_pos = path.rfind(".")
    if dot_pos == -1:
        return False
    ext = path[dot_pos:].lower()
    return ext in BINARY_EXTENSIONS


def is_binary_by_content(data: bytes) -> bool:
    """Check if content is binary by looking for null bytes in the first 8KB."""
    return b"\x00" in data[:8192]


def get_language_hint(path: str) -> str:
    """Return the Markdown code-fence language hint for a file path."""
    filename = path.rsplit("/", maxsplit=1)[-1] if "/" in path else path

    # Check special filenames first
    if filename in FILENAME_LANGUAGE_MAP:
        return FILENAME_LANGUAGE_MAP[filename]

    dot_pos = path.rfind(".")
    if dot_pos == -1:
        return ""
    ext = path[dot_pos:]
    return LANGUAGE_MAP.get(ext, LANGUAGE_MAP.get(ext.lower(), ""))


# ---------------------------------------------------------------------------
# Regex path filtering
# ---------------------------------------------------------------------------


def parse_pattern_input(raw: str) -> list[str]:
    """Split a comma-separated string into individual pattern strings.

    Whitespace around each pattern is stripped. Empty segments are ignored.
    """
    if not raw or not raw.strip():
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def validate_patterns(patterns: list[str]) -> list[str]:
    """Return a list of error messages for invalid regex patterns.

    An empty list means all patterns are valid.
    """
    errors: list[str] = []
    for p in patterns:
        try:
            re.compile(p)
        except re.error as exc:
            errors.append(f"`{p}` — {exc}")
    return errors


def compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    """Compile a list of regex pattern strings. Invalid ones are silently skipped."""
    compiled: list[re.Pattern[str]] = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error:
            pass
    return compiled


def matches_any_pattern(path: str, compiled: list[re.Pattern[str]]) -> bool:
    """Return True if the path matches **any** of the compiled patterns.

    Uses `re.search` so the pattern can match anywhere in the path.
    If *compiled* is empty every path matches (no filter).
    """
    if not compiled:
        return True
    return any(pat.search(path) for pat in compiled)
