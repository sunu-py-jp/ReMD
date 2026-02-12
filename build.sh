#!/usr/bin/env bash
# ----------------------------------------------------------
# ReMD — macOS build script
#
# Usage:
#   chmod +x build.sh   (初回のみ)
#   ./build.sh
#
# Python 3.10 以上が必要です。
# 依存パッケージは自動でインストールされます。
# ----------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

# ---- Python を探す ----
if command -v python3 &>/dev/null; then
    PY=python3
elif command -v python &>/dev/null; then
    PY=python
else
    echo "Error: Python が見つかりません。Python 3.10 以上をインストールしてください。"
    exit 1
fi

echo "Using Python: $($PY --version 2>&1)"
echo

$PY build.py
