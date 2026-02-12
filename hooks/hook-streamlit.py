"""PyInstaller hook for Streamlit.

Collects Streamlit's data files and hidden imports that PyInstaller
cannot detect automatically.
"""

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    copy_metadata,
)

# Streamlit needs its static assets and metadata
datas = collect_data_files("streamlit")
datas += copy_metadata("streamlit")

# Collect all submodules — Streamlit uses dynamic imports
hiddenimports = collect_submodules("streamlit")
