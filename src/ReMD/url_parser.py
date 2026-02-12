"""URL parsing and provider auto-detection."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from ReMD.models import ProviderType, RepoInfo


class URLParseError(Exception):
    """Raised when a URL cannot be parsed."""


def parse_repo_url(url: str) -> RepoInfo:
    """Parse a repository URL and return RepoInfo.

    Supported formats:
      - https://github.com/owner/repo
      - https://github.com/owner/repo/tree/branch
      - https://github.com/owner/repo/tree/branch/with/slashes
      - https://dev.azure.com/org/project/_git/repo
      - https://dev.azure.com/org/project/_git/repo?version=GBbranch
      - https://org.visualstudio.com/project/_git/repo
    """
    url = url.strip()
    if not url:
        raise URLParseError("URL is empty.")

    parsed = urlparse(url)
    if not parsed.scheme:
        raise URLParseError(f"Invalid URL (no scheme): {url}")
    if parsed.scheme not in ("http", "https"):
        raise URLParseError(f"Unsupported scheme: {parsed.scheme}")

    host = parsed.hostname or ""
    path = parsed.path.strip("/")

    if host == "github.com":
        return _parse_github(path, url)
    elif host == "dev.azure.com":
        return _parse_azure_devops_new(path, parsed.query, url)
    elif host.endswith(".visualstudio.com"):
        org = host.removesuffix(".visualstudio.com")
        return _parse_azure_devops_old(org, path, parsed.query, url)
    else:
        raise URLParseError(f"Unsupported host: {host}")


def _parse_github(path: str, raw_url: str) -> RepoInfo:
    """Parse a GitHub URL path."""
    # path: owner/repo[/tree/branch[/...]]
    parts = path.split("/")
    if len(parts) < 2:
        raise URLParseError(f"GitHub URL must include owner/repo: {raw_url}")

    owner, repo = parts[0], parts[1]
    # Remove .git suffix if present
    repo = repo.removesuffix(".git")
    branch = None

    if len(parts) >= 4 and parts[2] == "tree":
        # Everything after /tree/ is the branch name (may contain slashes)
        branch = "/".join(parts[3:])

    return RepoInfo(
        provider=ProviderType.GITHUB,
        owner=owner,
        repo=repo,
        branch=branch,
        raw_url=raw_url,
    )


def _parse_azure_devops_new(path: str, query: str, raw_url: str) -> RepoInfo:
    """Parse dev.azure.com URL path: org/project/_git/repo"""
    parts = path.split("/")
    if len(parts) < 4 or parts[2] != "_git":
        raise URLParseError(
            f"Azure DevOps URL must match org/project/_git/repo: {raw_url}"
        )

    org, project, _, repo = parts[0], parts[1], parts[2], parts[3]
    branch = _extract_azdo_branch(query)

    return RepoInfo(
        provider=ProviderType.AZURE_DEVOPS,
        owner=org,
        repo=repo,
        branch=branch,
        project=project,
        raw_url=raw_url,
    )


def _parse_azure_devops_old(
    org: str, path: str, query: str, raw_url: str
) -> RepoInfo:
    """Parse org.visualstudio.com URL path: project/_git/repo"""
    parts = path.split("/")
    if len(parts) < 3 or parts[1] != "_git":
        raise URLParseError(
            f"Azure DevOps URL must match project/_git/repo: {raw_url}"
        )

    project, _, repo = parts[0], parts[1], parts[2]
    branch = _extract_azdo_branch(query)

    return RepoInfo(
        provider=ProviderType.AZURE_DEVOPS,
        owner=org,
        repo=repo,
        branch=branch,
        project=project,
        raw_url=raw_url,
    )


def _extract_azdo_branch(query: str) -> str | None:
    """Extract branch from Azure DevOps query string (version=GBbranch)."""
    match = re.search(r"version=GB(.+?)(?:&|$)", query)
    return match.group(1) if match else None
