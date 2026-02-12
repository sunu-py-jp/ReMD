"""Azure DevOps REST API provider."""

from __future__ import annotations

from typing import Generator

import requests

from ReMD.file_filter import get_language_hint, is_binary_by_extension
from ReMD.models import FetchProgress, FileEntry, RepoInfo
from ReMD.providers.base import RepoProvider


class AzureDevOpsError(Exception):
    """Raised for Azure DevOps API errors."""


class AzureDevOpsProvider(RepoProvider):
    """Provider for Azure DevOps repositories using the REST API."""

    API_VERSION = "7.1-preview.1"

    def __init__(self, pat: str | None = None):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "ReMD/1.0"
        if pat:
            self.session.auth = ("", pat)

    def _api_base(self, repo_info: RepoInfo) -> str:
        return (
            f"https://dev.azure.com/{repo_info.owner}/{repo_info.project}"
            f"/_apis/git/repositories/{repo_info.repo}"
        )

    def _api_get(
        self,
        repo_info: RepoInfo,
        path: str,
        params: dict | None = None,
    ) -> dict:
        url = f"{self._api_base(repo_info)}{path}"
        params = params or {}
        params["api-version"] = self.API_VERSION

        resp = self.session.get(url, params=params, timeout=30)

        if resp.status_code == 404:
            raise AzureDevOpsError(
                "Repository not found. Check the URL, or provide a PAT for private repos."
            )
        if resp.status_code == 401:
            raise AzureDevOpsError(
                "Authentication failed. Check your Personal Access Token."
            )
        if resp.status_code == 403:
            raise AzureDevOpsError(
                "Access denied. The PAT may lack permissions."
            )
        resp.raise_for_status()
        return resp.json()

    def get_default_branch(self, repo_info: RepoInfo) -> str:
        data = self._api_get(repo_info, "")
        default = data.get("defaultBranch", "refs/heads/main")
        # Remove "refs/heads/" prefix
        return default.removeprefix("refs/heads/")

    def list_files(self, repo_info: RepoInfo) -> list[FileEntry]:
        branch = repo_info.branch
        if not branch:
            branch = self.get_default_branch(repo_info)
            repo_info.branch = branch

        params = {
            "recursionLevel": "Full",
            "versionDescriptor.version": branch,
            "versionDescriptor.versionType": "branch",
        }
        data = self._api_get(repo_info, "/items", params=params)

        files: list[FileEntry] = []
        for item in data.get("value", []):
            if item.get("isFolder"):
                continue

            path = item.get("path", "").lstrip("/")
            if not path:
                continue

            is_binary = item.get("contentMetadata", {}).get("isBinary", False)
            if not is_binary:
                is_binary = is_binary_by_extension(path)

            files.append(
                FileEntry(
                    path=path,
                    size=item.get("size", 0) if not item.get("isFolder") else 0,
                    is_binary=is_binary,
                    language_hint=get_language_hint(path),
                )
            )
        return files

    def fetch_file_content(self, repo_info: RepoInfo, file_entry: FileEntry) -> str:
        branch = repo_info.branch or "main"
        params = {
            "path": f"/{file_entry.path}",
            "versionDescriptor.version": branch,
            "versionDescriptor.versionType": "branch",
            "includeContent": "true",
            "api-version": self.API_VERSION,
        }
        url = f"{self._api_base(repo_info)}/items"
        resp = self.session.get(
            url,
            params=params,
            timeout=30,
            headers={"Accept": "application/octet-stream"},
        )

        if resp.status_code == 404:
            raise AzureDevOpsError(f"File not found: {file_entry.path}")
        resp.raise_for_status()

        return resp.text

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
            except Exception as exc:
                # Retry once
                try:
                    content = self.fetch_file_content(repo_info, entry)
                    entry.content = content
                except Exception as retry_exc:
                    progress.errors.append(f"{entry.path}: {retry_exc}")

            progress.fetched_files += 1
            yield progress
