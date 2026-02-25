# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for ReMD.

Supports macOS and Windows.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

block_cipher = None
project_root = Path(SPECPATH)
is_windows = sys.platform == "win32"

# Collect streamlit and its full dependency tree
st_datas, st_binaries, st_hiddenimports = collect_all("streamlit")
st_datas += copy_metadata("streamlit")
st_datas += copy_metadata("altair")
st_datas += copy_metadata("packaging")

# Collect keyring metadata and only the platform-relevant backend
st_datas += copy_metadata("keyring")
if is_windows:
    _kr_backend_imports = ["keyring", "keyring.backends", "keyring.backends.Windows"]
    _kr_backend_excludes = ["keyring.backends.macOS", "keyring.backends.SecretService"]
else:
    _kr_backend_imports = ["keyring", "keyring.backends", "keyring.backends.macOS"]
    _kr_backend_excludes = ["keyring.backends.Windows", "keyring.backends.SecretService"]

a = Analysis(
    [str(project_root / "run.py")],
    pathex=[str(project_root / "src")],
    binaries=st_binaries,
    datas=[
        (str(project_root / "src" / "ReMD"), "src/ReMD"),
        (str(project_root / ".streamlit"), ".streamlit"),
    ] + st_datas,
    hiddenimports=[
        # Our package
        "ReMD",
        "ReMD.app",
        "ReMD.models",
        "ReMD.url_parser",
        "ReMD.file_filter",
        "ReMD.tree_builder",
        "ReMD.markdown_renderer",
        "ReMD.providers",
        "ReMD.providers.base",
        "ReMD.providers.github",
        "ReMD.providers.azure_devops",
        "ReMD.token_store",
        # Streamlit and key dependencies
        "streamlit",
        "streamlit.web",
        "streamlit.web.bootstrap",
        "streamlit.runtime",
        "streamlit.runtime.runtime",
    ] + st_hiddenimports + _kr_backend_imports
    + collect_submodules("streamlit"),
    hookspath=[str(project_root / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "tkinter",
        "matplotlib",
        "scipy",
        "IPython",
        "notebook",
        "nbformat",
        "black",
        "lxml",
    ] + _kr_backend_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ReMD",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    # Windows-only: set icon if available
    icon=str(project_root / "icon.ico") if is_windows and (project_root / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ReMD",
)
