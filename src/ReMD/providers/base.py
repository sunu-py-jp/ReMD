"""Abstract base class for repository providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generator

from ReMD.models import FetchProgress, FileEntry, RepoInfo


class RepoProvider(ABC):
    """Base class for Git hosting service providers."""

    @abstractmethod
    def get_default_branch(self, repo_info: RepoInfo) -> str:
        """Return the default branch name for the repository."""

    @abstractmethod
    def list_files(self, repo_info: RepoInfo) -> list[FileEntry]:
        """List all files in the repository."""

    @abstractmethod
    def fetch_file_content(self, repo_info: RepoInfo, file_entry: FileEntry) -> str:
        """Fetch the content of a single file."""

    def fetch_all_files(
        self,
        repo_info: RepoInfo,
        files: list[FileEntry],
        max_file_size: int = 1_000_000,
    ) -> Generator[FetchProgress, None, None]:
        """Fetch content for all files, yielding progress updates.

        Args:
            repo_info: Repository information.
            files: List of files to fetch.
            max_file_size: Skip files larger than this (bytes). Default 1MB.
        """
        progress = FetchProgress(total_files=len(files))

        for entry in files:
            progress.current_file = entry.path

            if entry.is_binary:
                progress.skipped_binary += 1
                progress.fetched_files += 1
                yield progress
                continue

            if entry.size > max_file_size > 0:
                progress.skipped_binary += 1
                progress.fetched_files += 1
                yield progress
                continue

            try:
                content = self.fetch_file_content(repo_info, entry)
                entry.content = content
            except Exception as exc:
                progress.errors.append(f"{entry.path}: {exc}")

            progress.fetched_files += 1
            yield progress
