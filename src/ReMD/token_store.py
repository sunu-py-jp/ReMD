"""Secure token storage using OS keychain (macOS Keychain / Windows Credential Manager)."""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

_SERVICE_NAME = "ReMD"
_AVAILABLE = False

try:
    import keyring
    import keyring.errors

    # PyInstaller frozen bundles cannot auto-detect keyring backends
    # via entry points, so we set them explicitly.
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            from keyring.backends import macOS

            keyring.set_keyring(macOS.Keyring())
        elif sys.platform == "win32":
            from keyring.backends import Windows

            keyring.set_keyring(Windows.WinVaultKeyring())

    _AVAILABLE = True
except Exception:
    logger.warning("keyring not available; token persistence disabled")


def is_available() -> bool:
    """Return True if the OS keychain is usable."""
    return _AVAILABLE


def load(key: str) -> str | None:
    """Load a token from the OS keychain. Returns None on failure."""
    if not _AVAILABLE:
        return None
    try:
        return keyring.get_password(_SERVICE_NAME, key)
    except Exception:
        return None


def save(key: str, value: str) -> bool:
    """Save a token to the OS keychain. Returns True on success."""
    if not _AVAILABLE or not value:
        return False
    try:
        keyring.set_password(_SERVICE_NAME, key, value)
        return True
    except Exception:
        logger.warning("Failed to save %s to keyring", key)
        return False


def delete(key: str) -> bool:
    """Delete a token from the OS keychain. Returns True on success."""
    if not _AVAILABLE:
        return False
    try:
        keyring.delete_password(_SERVICE_NAME, key)
        return True
    except Exception:
        return False
