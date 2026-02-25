"""Cross-platform build automation script for ReMD.

Supports:
  - macOS (arm64 / x86_64)
  - Windows 10 / 11
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path


def _ensure_dependencies() -> None:
    """Install build & runtime dependencies if missing."""
    deps = ["streamlit", "requests", "keyring", "pyinstaller"]
    for dep in deps:
        try:
            __import__(dep if dep != "pyinstaller" else "PyInstaller")
        except ImportError:
            print(f"Installing {dep} ...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", dep],
                stdout=subprocess.DEVNULL,
            )


def _remove_pathlib_backport() -> None:
    """Remove the obsolete 'pathlib' backport that breaks PyInstaller."""
    try:
        import importlib.metadata as md

        md.distribution("pathlib")
        print("Removing obsolete 'pathlib' backport ...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "uninstall", "pathlib", "-y"],
            stdout=subprocess.DEVNULL,
        )
    except Exception:
        pass


def main() -> None:
    project_root = Path(__file__).resolve().parent
    spec_file = project_root / "ReMD.spec"

    if not spec_file.exists():
        print(f"Error: {spec_file} not found.")
        sys.exit(1)

    os_name = platform.system()    # Darwin / Windows / Linux
    arch = platform.machine()      # arm64 / x86_64 / AMD64
    print(f"=== ReMD build ===")
    print(f"OS:       {os_name}")
    print(f"Arch:     {arch}")
    print(f"Python:   {sys.version}")
    print()

    # ---- Pre-build checks ----
    _ensure_dependencies()
    _remove_pathlib_backport()

    # ---- Clean previous build ----
    for d in ("build", "dist"):
        target = project_root / d
        if target.exists():
            print(f"Cleaning {target} ...")
            shutil.rmtree(target)

    # ---- Run PyInstaller ----
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec_file),
        "--clean",
        "--noconfirm",
    ]

    print(f"Running: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=str(project_root))

    if result.returncode != 0:
        print()
        print("=== Build FAILED ===")
        sys.exit(result.returncode)

    # ---- Report ----
    dist_dir = project_root / "dist" / "ReMD"
    exe_name = "ReMD.exe" if os_name == "Windows" else "ReMD"
    exe_path = dist_dir / exe_name

    # Calculate size
    total_bytes = sum(f.stat().st_size for f in dist_dir.rglob("*") if f.is_file())
    size_mb = total_bytes / (1024 * 1024)

    print()
    print("=== Build successful! ===")
    print(f"Output:   {dist_dir}")
    print(f"Binary:   {exe_path}")
    print(f"Size:     {size_mb:.0f} MB")
    print()
    if os_name == "Windows":
        print(f'Run:  "{exe_path}"')
    else:
        print(f"Run:  {exe_path}")


if __name__ == "__main__":
    main()
