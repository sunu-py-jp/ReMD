"""GitHub REST API provider."""

from __future__ import annotations

import time
from typing import Generator

import requests

from ReMD.file_filter import get_language_hint, is_binary_by_extension
from ReMD.models import FetchProgress, FileEntry, RepoInfo
from ReMD.providers.base import RepoProvider


class GitHubError(Exception):
    """Raised for GitHub API errors."""


class RateLimitError(GitHubError):
    """Raised when GitHub rate limit is exceeded."""

    def __init__(self, reset_at: int):
        self.reset_at = reset_at
        wait = max(0, reset_at - int(time.time()))
        super().__init__(
            f"GitHub API rate limit exceeded. Resets in {wait} seconds."
        )


class GitHubProvider(RepoProvider):
    """Provider for GitHub repositories using the REST API."""

    API_BASE = "https://api.github.com"
    RAW_BASE = "https://raw.githubusercontent.com"

    def __init__(self, token: str | None = None):
        self.session = requests.Session()
        self.session.headers["Accept"] = "application/vnd.github+json"
        self.session.headers["User-Agent"] = "ReMD/1.0"
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _check_rate_limit(self, response: requests.Response) -> None:
        remaining = response.headers.get("X-RateLimit-Remaining")
        if remaining is not None and int(remaining) == 0:
            reset_at = int(response.headers.get("X-RateLimit-Reset", 0))
            raise RateLimitError(reset_at)

    def _api_get(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.API_BASE}{path}"
        resp = self.session.get(url, params=params, timeout=30)
        self._check_rate_limit(resp)

        if resp.status_code == 404:
            raise GitHubError(
                "Repository not found. Check the URL, or provide a token for private repos."
            )
        if resp.status_code == 401:
            raise GitHubError("Authentication failed. Check your GitHub token.")
        if resp.status_code == 403:
            raise GitHubError(
                "Access denied. The token may lack permissions, or rate limit exceeded."
            )
        resp.raise_for_status()
        return resp.json()

    def get_default_branch(self, repo_info: RepoInfo) -> str:
        data = self._api_get(f"/repos/{repo_info.owner}/{repo_info.repo}")
        return data["default_branch"]

    def list_files(self, repo_info: RepoInfo) -> list[FileEntry]:
        branch = repo_info.branch
        if not branch:
            branch = self.get_default_branch(repo_info)
            repo_info.branch = branch

        data = self._api_get(
            f"/repos/{repo_info.owner}/{repo_info.repo}/git/trees/{branch}",
            params={"recursive": "1"},
        )

        if data.get("truncated"):
            # For very large repos, fall back to non-recursive traversal
            return self._list_files_non_recursive(repo_info, branch, data)

        files: list[FileEntry] = []
        for item in data.get("tree", []):
            if item["type"] != "blob":
                continue
            path = item["path"]
            size = item.get("size", 0)
            binary = is_binary_by_extension(path)
            files.append(
                FileEntry(
                    path=path,
                    size=size,
                    is_binary=binary,
                    language_hint=get_language_hint(path),
                )
            )
        return files

    def _list_files_non_recursive(
        self, repo_info: RepoInfo, branch: str, initial_data: dict
    ) -> list[FileEntry]:
        """Handle truncated tree by walking directories individually."""
        files: list[FileEntry] = []
        dirs_to_visit: list[str] = []

        for item in initial_data.get("tree", []):
            if item["type"] == "blob":
                path = item["path"]
                files.append(
                    FileEntry(
                        path=path,
                        size=item.get("size", 0),
                        is_binary=is_binary_by_extension(path),
                        language_hint=get_language_hint(path),
                    )
                )
            elif item["type"] == "tree":
                dirs_to_visit.append(item["sha"])

        for sha in dirs_to_visit:
            try:
                sub_data = self._api_get(
                    f"/repos/{repo_info.owner}/{repo_info.repo}/git/trees/{sha}",
                    params={"recursive": "1"},
                )
                for item in sub_data.get("tree", []):
                    if item["type"] == "blob":
                        path = item["path"]
                        files.append(
                            FileEntry(
                                path=path,
                                size=item.get("size", 0),
                                is_binary=is_binary_by_extension(path),
                                language_hint=get_language_hint(path),
                            )
                        )
            except Exception:
                continue

        return files

    def fetch_file_content(self, repo_info: RepoInfo, file_entry: FileEntry) -> str:
        branch = repo_info.branch or "main"

        # Try raw.githubusercontent.com first (fast, no API rate limit)
        raw_url = (
            f"{self.RAW_BASE}/{repo_info.owner}/{repo_info.repo}"
            f"/{branch}/{file_entry.path}"
        )
        try:
            resp = self.session.get(raw_url, timeout=30)
            if resp.status_code == 200:
                return resp.text
        except requests.RequestException:
            pass

        # Fallback to Contents API (works for private repos with token)
        data = self._api_get(
            f"/repos/{repo_info.owner}/{repo_info.repo}/contents/{file_entry.path}",
            params={"ref": branch},
        )
        import base64

        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return data.get("content", "")

    def fetch_all_files(
        self,
        repo_info: RepoInfo,
        files: list[FileEntry],
        max_file_size: int = 1_000_000,
    ) -> Generator[FetchProgress, None, None]:
        progress = FetchProgress(total_files=len(files))

        for entry in files:
            progress.current_file = entry.path

            if entry.is_binary:
                progress.skipped_binary += 1
                progress.fetched_files += 1
                yield progress
                continue

            if max_file_size > 0 and entry.size > max_file_size:
                progress.skipped_binary += 1
                progress.fetched_files += 1
                yield progress
                continue

            try:
                content = self.fetch_file_content(repo_info, entry)
                entry.content = content
            except RateLimitError:
                raise
            except Exception as exc:
                # Retry once
                try:
                    content = self.fetch_file_content(repo_info, entry)
                    entry.content = content
                except Exception as retry_exc:
                    progress.errors.append(f"{entry.path}: {retry_exc}")

            progress.fetched_files += 1
            yield progress
