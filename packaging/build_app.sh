#!/usr/bin/env bash
# Build the macOS Voice Memos Exporter app bundle with PyInstaller.

set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(dirname -- "$SCRIPT_DIR")
cd "$REPO_ROOT"

PYINSTALLER="$REPO_ROOT/.venv-package/bin/pyinstaller"
if [ ! -x "$PYINSTALLER" ]; then
    echo "error: .venv-package/bin/pyinstaller is missing or not executable" >&2
    echo "run: /opt/homebrew/bin/python3.14 -m venv .venv-package && .venv-package/bin/python -m pip install pyinstaller" >&2
    exit 1
fi

export PYINSTALLER_CONFIG_DIR="$REPO_ROOT/build/pyinstaller-cache"
"$PYINSTALLER" --noconfirm --clean packaging/voice_memos_exporter.spec

APP_PATH="$REPO_ROOT/dist/Voice Memos Exporter.app"
echo "Bundle: $APP_PATH"
du -sh "$APP_PATH"
echo "CFBundleIdentifier: $(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP_PATH/Contents/Info.plist")"
