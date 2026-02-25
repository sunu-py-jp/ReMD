"""Tests for token_store module."""

from unittest import mock


class TestIsAvailable:
    def test_returns_bool(self):
        from ReMD import token_store

        assert isinstance(token_store.is_available(), bool)


class TestLoadWhenUnavailable:
    def test_returns_none(self):
        from ReMD import token_store

        with mock.patch.object(token_store, "_AVAILABLE", False):
            assert token_store.load("any_key") is None


class TestSaveWhenUnavailable:
    def test_returns_false(self):
        from ReMD import token_store

        with mock.patch.object(token_store, "_AVAILABLE", False):
            assert token_store.save("key", "value") is False

    def test_empty_value_returns_false(self):
        from ReMD import token_store

        with mock.patch.object(token_store, "_AVAILABLE", True):
            assert token_store.save("key", "") is False


class TestDeleteWhenUnavailable:
    def test_returns_false(self):
        from ReMD import token_store

        with mock.patch.object(token_store, "_AVAILABLE", False):
            assert token_store.delete("any_key") is False


class TestLoadWithKeyring:
    def test_returns_password(self):
        from ReMD import token_store

        mock_keyring = mock.MagicMock()
        mock_keyring.get_password.return_value = "my-token"
        with mock.patch.object(token_store, "_AVAILABLE", True), \
             mock.patch.dict(token_store.__dict__, {"keyring": mock_keyring}):
            result = token_store.load("github_token")
            assert result == "my-token"
            mock_keyring.get_password.assert_called_once_with("ReMD", "github_token")

    def test_returns_none_on_exception(self):
        from ReMD import token_store

        mock_keyring = mock.MagicMock()
        mock_keyring.get_password.side_effect = Exception("keyring error")
        with mock.patch.object(token_store, "_AVAILABLE", True), \
             mock.patch.dict(token_store.__dict__, {"keyring": mock_keyring}):
            result = token_store.load("github_token")
            assert result is None


class TestSaveWithKeyring:
    def test_saves_and_returns_true(self):
        from ReMD import token_store

        mock_keyring = mock.MagicMock()
        with mock.patch.object(token_store, "_AVAILABLE", True), \
             mock.patch.dict(token_store.__dict__, {"keyring": mock_keyring}):
            result = token_store.save("github_token", "my-token")
            assert result is True
            mock_keyring.set_password.assert_called_once_with(
                "ReMD", "github_token", "my-token"
            )

    def test_returns_false_on_exception(self):
        from ReMD import token_store

        mock_keyring = mock.MagicMock()
        mock_keyring.set_password.side_effect = Exception("keyring error")
        with mock.patch.object(token_store, "_AVAILABLE", True), \
             mock.patch.dict(token_store.__dict__, {"keyring": mock_keyring}):
            result = token_store.save("github_token", "my-token")
            assert result is False


class TestDeleteWithKeyring:
    def test_deletes_and_returns_true(self):
        from ReMD import token_store

        mock_keyring = mock.MagicMock()
        with mock.patch.object(token_store, "_AVAILABLE", True), \
             mock.patch.dict(token_store.__dict__, {"keyring": mock_keyring}):
            result = token_store.delete("github_token")
            assert result is True
            mock_keyring.delete_password.assert_called_once_with("ReMD", "github_token")

    def test_returns_false_on_exception(self):
        from ReMD import token_store

        mock_keyring = mock.MagicMock()
        mock_keyring.delete_password.side_effect = Exception("keyring error")
        with mock.patch.object(token_store, "_AVAILABLE", True), \
             mock.patch.dict(token_store.__dict__, {"keyring": mock_keyring}):
            result = token_store.delete("github_token")
            assert result is False
