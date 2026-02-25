"""Data classes for ReMD."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ProviderType(Enum):
    GITHUB = "github"
    AZURE_DEVOPS = "azure_devops"


@dataclass
class RepoInfo:
    provider: ProviderType
    owner: str
    repo: str
    branch: str | None = None
    project: str | None = None  # Azure DevOps only
    api_host: str = "github.com"
    raw_url: str = ""


@dataclass
class FileEntry:
    path: str
    size: int = 0
    is_binary: bool = False
    content: str | None = None
    language_hint: str = ""


@dataclass
class FetchProgress:
    total_files: int = 0
    fetched_files: int = 0
    skipped_binary: int = 0
    current_file: str = ""
    errors: list[str] = field(default_factory=list)
