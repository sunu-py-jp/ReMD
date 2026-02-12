"""Tests for GitHub provider."""

import responses
import pytest

from ReMD.models import FileEntry, ProviderType, RepoInfo
from ReMD.providers.github import GitHubError, GitHubProvider, RateLimitError


def _repo_info(branch: str | None = "main") -> RepoInfo:
    return RepoInfo(
        provider=ProviderType.GITHUB,
        owner="testowner",
        repo="testrepo",
        branch=branch,
    )


class TestGetDefaultBranch:
    @responses.activate
    def test_returns_default_branch(self):
        responses.add(
            responses.GET,
            "https://api.github.com/repos/testowner/testrepo",
            json={"default_branch": "main"},
            status=200,
        )
        provider = GitHubProvider()
        assert provider.get_default_branch(_repo_info(None)) == "main"

    @responses.activate
    def test_404_raises(self):
        responses.add(
            responses.GET,
            "https://api.github.com/repos/testowner/testrepo",
            json={"message": "Not Found"},
            status=404,
        )
        provider = GitHubProvider()
        with pytest.raises(GitHubError, match="not found"):
            provider.get_default_branch(_repo_info(None))


class TestListFiles:
    @responses.activate
    def test_lists_blobs(self):
        responses.add(
            responses.GET,
            "https://api.github.com/repos/testowner/testrepo/git/trees/main",
            json={
                "sha": "abc",
                "truncated": False,
                "tree": [
                    {"type": "blob", "path": "README.md", "size": 100},
                    {"type": "blob", "path": "src/main.py", "size": 200},
                    {"type": "tree", "path": "src", "size": 0},
                    {"type": "blob", "path": "logo.png", "size": 5000},
                ],
            },
            status=200,
        )
        provider = GitHubProvider()
        files = provider.list_files(_repo_info())
        assert len(files) == 3
        paths = [f.path for f in files]
        assert "README.md" in paths
        assert "src/main.py" in paths
        assert "logo.png" in paths

        # logo.png should be marked binary
        png_file = next(f for f in files if f.path == "logo.png")
        assert png_file.is_binary is True

    @responses.activate
    def test_resolves_default_branch_if_none(self):
        responses.add(
            responses.GET,
            "https://api.github.com/repos/testowner/testrepo",
            json={"default_branch": "develop"},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.github.com/repos/testowner/testrepo/git/trees/develop",
            json={"sha": "abc", "truncated": False, "tree": []},
            status=200,
        )
        provider = GitHubProvider()
        info = _repo_info(branch=None)
        files = provider.list_files(info)
        assert files == []
        assert info.branch == "develop"


class TestFetchFileContent:
    @responses.activate
    def test_raw_githubusercontent(self):
        responses.add(
            responses.GET,
            "https://raw.githubusercontent.com/testowner/testrepo/main/README.md",
            body="# Hello",
            status=200,
        )
        provider = GitHubProvider()
        entry = FileEntry(path="README.md", size=7)
        content = provider.fetch_file_content(_repo_info(), entry)
        assert content == "# Hello"

    @responses.activate
    def test_fallback_to_contents_api(self):
        import base64

        responses.add(
            responses.GET,
            "https://raw.githubusercontent.com/testowner/testrepo/main/secret.py",
            status=404,
        )
        encoded = base64.b64encode(b"print('hi')").decode()
        responses.add(
            responses.GET,
            "https://api.github.com/repos/testowner/testrepo/contents/secret.py",
            json={"content": encoded, "encoding": "base64"},
            status=200,
        )
        provider = GitHubProvider()
        entry = FileEntry(path="secret.py", size=11)
        content = provider.fetch_file_content(_repo_info(), entry)
        assert content == "print('hi')"


class TestRateLimit:
    @responses.activate
    def test_rate_limit_raises(self):
        responses.add(
            responses.GET,
            "https://api.github.com/repos/testowner/testrepo",
            json={"message": "rate limit"},
            status=200,
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "9999999999",
            },
        )
        provider = GitHubProvider()
        with pytest.raises(RateLimitError):
            provider.get_default_branch(_repo_info(None))


class TestFetchAllFiles:
    @responses.activate
    def test_skips_binary_and_large(self):
        responses.add(
            responses.GET,
            "https://raw.githubusercontent.com/testowner/testrepo/main/small.py",
            body="x = 1",
            status=200,
        )
        provider = GitHubProvider()
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
