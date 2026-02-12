"""Tests for url_parser module."""

import pytest

from ReMD.models import ProviderType
from ReMD.url_parser import URLParseError, parse_repo_url


class TestGitHubURLs:
    def test_basic(self):
        info = parse_repo_url("https://github.com/owner/repo")
        assert info.provider == ProviderType.GITHUB
        assert info.owner == "owner"
        assert info.repo == "repo"
        assert info.branch is None

    def test_with_branch(self):
        info = parse_repo_url("https://github.com/owner/repo/tree/main")
        assert info.owner == "owner"
        assert info.repo == "repo"
        assert info.branch == "main"

    def test_with_branch_slashes(self):
        info = parse_repo_url(
            "https://github.com/owner/repo/tree/feature/my-branch"
        )
        assert info.branch == "feature/my-branch"

    def test_dot_git_suffix(self):
        info = parse_repo_url("https://github.com/owner/repo.git")
        assert info.repo == "repo"

    def test_trailing_slash(self):
        info = parse_repo_url("https://github.com/owner/repo/")
        assert info.repo == "repo"

    def test_whitespace_stripped(self):
        info = parse_repo_url("  https://github.com/owner/repo  ")
        assert info.repo == "repo"


class TestAzureDevOpsURLs:
    def test_new_format(self):
        info = parse_repo_url("https://dev.azure.com/org/project/_git/repo")
        assert info.provider == ProviderType.AZURE_DEVOPS
        assert info.owner == "org"
        assert info.project == "project"
        assert info.repo == "repo"
        assert info.branch is None

    def test_new_format_with_branch(self):
        info = parse_repo_url(
            "https://dev.azure.com/org/project/_git/repo?version=GBmain"
        )
        assert info.branch == "main"

    def test_old_format(self):
        info = parse_repo_url(
            "https://myorg.visualstudio.com/project/_git/repo"
        )
        assert info.provider == ProviderType.AZURE_DEVOPS
        assert info.owner == "myorg"
        assert info.project == "project"
        assert info.repo == "repo"

    def test_old_format_with_branch(self):
        info = parse_repo_url(
            "https://myorg.visualstudio.com/project/_git/repo?version=GBdev"
        )
        assert info.branch == "dev"


class TestErrors:
    def test_empty(self):
        with pytest.raises(URLParseError, match="empty"):
            parse_repo_url("")

    def test_no_scheme(self):
        with pytest.raises(URLParseError, match="no scheme"):
            parse_repo_url("github.com/owner/repo")

    def test_unsupported_host(self):
        with pytest.raises(URLParseError, match="Unsupported host"):
            parse_repo_url("https://gitlab.com/owner/repo")

    def test_github_missing_repo(self):
        with pytest.raises(URLParseError, match="owner/repo"):
            parse_repo_url("https://github.com/owner")

    def test_azure_bad_path(self):
        with pytest.raises(URLParseError):
            parse_repo_url("https://dev.azure.com/org/project/repo")

    def test_unsupported_scheme(self):
        with pytest.raises(URLParseError, match="Unsupported scheme"):
            parse_repo_url("ftp://github.com/owner/repo")
