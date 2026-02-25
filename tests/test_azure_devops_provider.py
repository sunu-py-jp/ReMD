"""Tests for Azure DevOps provider."""

import responses
import pytest

from ReMD.models import FileEntry, ProviderType, RepoInfo
from ReMD.providers.azure_devops import AzureDevOpsError, AzureDevOpsProvider


def _repo_info(branch: str | None = "main") -> RepoInfo:
    return RepoInfo(
        provider=ProviderType.AZURE_DEVOPS,
        owner="myorg",
        repo="myrepo",
        branch=branch,
        project="myproject",
    )


API_BASE = "https://dev.azure.com/myorg/myproject/_apis/git/repositories/myrepo"


class TestGetDefaultBranch:
    @responses.activate
    def test_returns_default_branch(self):
        responses.add(
            responses.GET,
            API_BASE,
            json={"defaultBranch": "refs/heads/develop"},
            status=200,
        )
        provider = AzureDevOpsProvider()
        assert provider.get_default_branch(_repo_info(None)) == "develop"

    @responses.activate
    def test_strips_refs_heads_prefix(self):
        responses.add(
            responses.GET,
            API_BASE,
            json={"defaultBranch": "refs/heads/main"},
            status=200,
        )
        provider = AzureDevOpsProvider()
        assert provider.get_default_branch(_repo_info(None)) == "main"

    @responses.activate
    def test_defaults_to_main_when_missing(self):
        responses.add(
            responses.GET,
            API_BASE,
            json={},
            status=200,
        )
        provider = AzureDevOpsProvider()
        assert provider.get_default_branch(_repo_info(None)) == "main"

    @responses.activate
    def test_404_raises(self):
        responses.add(
            responses.GET,
            API_BASE,
            json={"message": "Not Found"},
            status=404,
        )
        provider = AzureDevOpsProvider()
        with pytest.raises(AzureDevOpsError, match="not found"):
            provider.get_default_branch(_repo_info(None))

    @responses.activate
    def test_401_raises(self):
        responses.add(
            responses.GET,
            API_BASE,
            json={"message": "Unauthorized"},
            status=401,
        )
        provider = AzureDevOpsProvider()
        with pytest.raises(AzureDevOpsError, match="Authentication failed"):
            provider.get_default_branch(_repo_info(None))

    @responses.activate
    def test_403_raises(self):
        responses.add(
            responses.GET,
            API_BASE,
            json={"message": "Forbidden"},
            status=403,
        )
        provider = AzureDevOpsProvider()
        with pytest.raises(AzureDevOpsError, match="Access denied"):
            provider.get_default_branch(_repo_info(None))


class TestListFiles:
    @responses.activate
    def test_lists_files_skipping_folders(self):
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            json={
                "value": [
                    {"path": "/src/main.py", "size": 100, "isFolder": False},
                    {"path": "/src", "isFolder": True},
                    {"path": "/README.md", "size": 50, "isFolder": False},
                ]
            },
            status=200,
        )
        provider = AzureDevOpsProvider()
        files = provider.list_files(_repo_info())
        assert len(files) == 2
        paths = [f.path for f in files]
        assert "src/main.py" in paths
        assert "README.md" in paths

    @responses.activate
    def test_detects_binary_from_metadata(self):
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            json={
                "value": [
                    {
                        "path": "/image.dat",
                        "size": 5000,
                        "isFolder": False,
                        "contentMetadata": {"isBinary": True},
                    },
                ]
            },
            status=200,
        )
        provider = AzureDevOpsProvider()
        files = provider.list_files(_repo_info())
        assert len(files) == 1
        assert files[0].is_binary is True

    @responses.activate
    def test_detects_binary_by_extension(self):
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            json={
                "value": [
                    {"path": "/logo.png", "size": 5000, "isFolder": False},
                ]
            },
            status=200,
        )
        provider = AzureDevOpsProvider()
        files = provider.list_files(_repo_info())
        assert files[0].is_binary is True

    @responses.activate
    def test_resolves_default_branch_if_none(self):
        responses.add(
            responses.GET,
            API_BASE,
            json={"defaultBranch": "refs/heads/develop"},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            json={"value": []},
            status=200,
        )
        provider = AzureDevOpsProvider()
        info = _repo_info(branch=None)
        files = provider.list_files(info)
        assert files == []
        assert info.branch == "develop"

    @responses.activate
    def test_sets_language_hint(self):
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            json={
                "value": [
                    {"path": "/app.py", "size": 100, "isFolder": False},
                ]
            },
            status=200,
        )
        provider = AzureDevOpsProvider()
        files = provider.list_files(_repo_info())
        assert files[0].language_hint == "python"

    @responses.activate
    def test_strips_leading_slash_from_path(self):
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            json={
                "value": [
                    {"path": "/src/main.py", "size": 100, "isFolder": False},
                ]
            },
            status=200,
        )
        provider = AzureDevOpsProvider()
        files = provider.list_files(_repo_info())
        assert files[0].path == "src/main.py"


class TestFetchFileContent:
    @responses.activate
    def test_fetches_content(self):
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            body="print('hello')",
            status=200,
        )
        provider = AzureDevOpsProvider()
        entry = FileEntry(path="main.py", size=14)
        content = provider.fetch_file_content(_repo_info(), entry)
        assert content == "print('hello')"

    @responses.activate
    def test_404_raises(self):
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            json={"message": "Not Found"},
            status=404,
        )
        provider = AzureDevOpsProvider()
        entry = FileEntry(path="missing.py", size=0)
        with pytest.raises(AzureDevOpsError, match="File not found"):
            provider.fetch_file_content(_repo_info(), entry)


class TestFetchAllFiles:
    @responses.activate
    def test_skips_binary_and_large(self):
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            body="x = 1",
            status=200,
        )
        provider = AzureDevOpsProvider()
        files = [
            FileEntry(path="logo.png", size=5000, is_binary=True),
            FileEntry(path="huge.dat", size=2_000_000),
            FileEntry(path="small.py", size=5),
        ]
        results = list(provider.fetch_all_files(_repo_info(), files, max_file_size=1_000_000))
        assert len(results) == 3
        final = results[-1]
        assert final.fetched_files == 3
        assert final.skipped_binary == 2
        assert files[2].content == "x = 1"

    @responses.activate
    def test_progress_tracking(self):
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            body="content",
            status=200,
        )
        provider = AzureDevOpsProvider()
        files = [
            FileEntry(path="a.py", size=7),
        ]
        results = list(provider.fetch_all_files(_repo_info(), files))
        assert len(results) == 1
        assert results[0].current_file == "a.py"
        assert results[0].fetched_files == 1
        assert results[0].total_files == 1

    @responses.activate
    def test_retry_on_failure(self):
        # First attempt fails, retry succeeds
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            body=Exception("connection error"),
        )
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            body="recovered",
            status=200,
        )
        provider = AzureDevOpsProvider()
        files = [FileEntry(path="retry.py", size=9)]
        results = list(provider.fetch_all_files(_repo_info(), files))
        assert files[0].content == "recovered"
        assert results[-1].errors == []

    @responses.activate
    def test_error_appended_on_double_failure(self):
        # Both attempts fail
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            body=Exception("fail 1"),
        )
        responses.add(
            responses.GET,
            f"{API_BASE}/items",
            body=Exception("fail 2"),
        )
        provider = AzureDevOpsProvider()
        files = [FileEntry(path="bad.py", size=5)]
        results = list(provider.fetch_all_files(_repo_info(), files))
        assert len(results[-1].errors) == 1
        assert "bad.py" in results[-1].errors[0]


class TestAuthentication:
    def test_pat_sets_auth(self):
        provider = AzureDevOpsProvider(pat="my-token")
        assert provider.session.auth == ("", "my-token")

    def test_no_pat_no_auth(self):
        provider = AzureDevOpsProvider()
        assert provider.session.auth is None
