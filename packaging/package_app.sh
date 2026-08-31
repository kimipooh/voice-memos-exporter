#!/usr/bin/env bash
# Package an already-built app. build_app.sh never packages or removes the app.

set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(dirname -- "$SCRIPT_DIR")
DIST_DIR="$REPO_ROOT/dist"
APP_PATH="$DIST_DIR/Voice Memos Exporter.app"
VERIFY_DIR=""

cleanup_verify_dir() {
    if [ -n "$VERIFY_DIR" ] && [ -d "$VERIFY_DIR" ]; then
        rm -rf "$VERIFY_DIR"
    fi
}
trap cleanup_verify_dir EXIT

fail() {
    echo "error: $*" >&2
    exit 1
}

plist_value() {
    /usr/libexec/PlistBuddy -c "Print :$2" "$1"
}

verify_bundle() {
    local bundle_path=$1
    local expected_version=$2
    local label=$3
    local plist_path="$bundle_path/Contents/Info.plist"
    local executable_path="$bundle_path/Contents/MacOS/Voice Memos Exporter"
    local identifier short_version bundle_version symlink_count

    echo "Verify $label bundle: $bundle_path"
    [ -d "$bundle_path" ] || fail "$label bundle is missing: $bundle_path"
    [ -f "$plist_path" ] || fail "$label bundle Info.plist is missing: $plist_path"
    /usr/bin/plutil -lint "$plist_path" >/dev/null || fail "$label Info.plist is invalid"

    identifier=$(plist_value "$plist_path" "CFBundleIdentifier") \
        || fail "$label CFBundleIdentifier is missing"
    [ "$identifier" = "jp.kitani.voicememosexporter" ] \
        || fail "$label CFBundleIdentifier is unexpected: $identifier"
    short_version=$(plist_value "$plist_path" "CFBundleShortVersionString") \
        || fail "$label CFBundleShortVersionString is missing"
    bundle_version=$(plist_value "$plist_path" "CFBundleVersion") \
        || fail "$label CFBundleVersion is missing"
    [ "$short_version" = "$expected_version" ] \
        || fail "$label CFBundleShortVersionString does not match $expected_version"
    [ "$bundle_version" = "$expected_version" ] \
        || fail "$label CFBundleVersion does not match $expected_version"

    [ -f "$executable_path" ] || fail "$label main executable is missing: $executable_path"
    [ -x "$executable_path" ] || fail "$label main executable is not executable: $executable_path"
    [ -d "$bundle_path/Contents/MacOS" ] || fail "$label Contents/MacOS is missing"
    [ -d "$bundle_path/Contents/Resources" ] || fail "$label Contents/Resources is missing"
    [ -d "$bundle_path/Contents/Frameworks" ] || fail "$label Contents/Frameworks is missing"

    symlink_count=$(find "$bundle_path" -type l | wc -l | tr -d ' ')
    [ "$symlink_count" -gt 0 ] || fail "$label bundle has no symbolic links"
    echo "$label symbolic links: $symlink_count"
}

[ -d "$APP_PATH" ] || fail "app bundle is missing: $APP_PATH (run: bash packaging/build_app.sh)"

INFO_PLIST="$APP_PATH/Contents/Info.plist"
[ -f "$INFO_PLIST" ] || fail "app bundle Info.plist is missing: $INFO_PLIST"
VERSION=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' \
    "$APP_PATH/Contents/Info.plist") \
    || fail "CFBundleShortVersionString is missing from $INFO_PLIST"
case "$VERSION" in
    [0-9]*.[0-9]*.[0-9]*) ;;
    *) fail "invalid CFBundleShortVersionString (expected X.Y.Z): $VERSION" ;;
esac
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    fail "invalid CFBundleShortVersionString (expected X.Y.Z): $VERSION"
fi

ZIP_NAME="Voice-Memos-Exporter-v${VERSION}-macOS-arm64.zip"
ZIP_PATH="$DIST_DIR/$ZIP_NAME"
if [ -e "$ZIP_PATH" ]; then
    ZIP_DETAILS=$(stat -f 'size=%z bytes, modified=%Sm' -t '%Y-%m-%d %H:%M:%S %Z' "$ZIP_PATH") \
        || ZIP_DETAILS="size and modified time unavailable"
    fail "refusing to overwrite existing ZIP: $ZIP_PATH ($ZIP_DETAILS)"
fi

echo "Bundle: $APP_PATH"
echo "Version: $VERSION"
verify_bundle "$APP_PATH" "$VERSION" "source"
SOURCE_SYMLINKS=$(find "$APP_PATH" -type l | wc -l | tr -d ' ')
SOURCE_FILES=$(find "$APP_PATH" -type f | wc -l | tr -d ' ')

echo "Create ZIP: $ZIP_PATH"
(
    cd "$DIST_DIR"
    ditto -c -k --sequesterRsrc --keepParent "Voice Memos Exporter.app" "$ZIP_NAME"
) || fail "could not create ZIP: $ZIP_PATH"

VERIFY_DIR=$(mktemp -d "${TMPDIR:-/tmp}/voice-memos-exporter-package.XXXXXX") \
    || fail "could not create a temporary verification directory"
echo "Verify ZIP integrity: $ZIP_PATH"
/usr/bin/unzip -t "$ZIP_PATH" >/dev/null || fail "ZIP integrity check failed: $ZIP_PATH"
echo "Expand ZIP in temporary directory: $VERIFY_DIR"
ditto -x -k "$ZIP_PATH" "$VERIFY_DIR" || fail "could not expand ZIP for verification"

EXTRACTED_APP="$VERIFY_DIR/Voice Memos Exporter.app"
verify_bundle "$EXTRACTED_APP" "$VERSION" "expanded"
EXTRACTED_SYMLINKS=$(find "$EXTRACTED_APP" -type l | wc -l | tr -d ' ')
EXTRACTED_FILES=$(find "$EXTRACTED_APP" -type f | wc -l | tr -d ' ')
[ "$SOURCE_SYMLINKS" = "$EXTRACTED_SYMLINKS" ] \
    || fail "symbolic-link count differs (source=$SOURCE_SYMLINKS, expanded=$EXTRACTED_SYMLINKS)"
[ "$SOURCE_FILES" = "$EXTRACTED_FILES" ] \
    || fail "regular-file count differs (source=$SOURCE_FILES, expanded=$EXTRACTED_FILES)"

SOURCE_PATHS="$VERIFY_DIR/source-paths.txt"
EXTRACTED_PATHS="$VERIFY_DIR/expanded-paths.txt"
(
    cd "$APP_PATH"
    find . -print | LC_ALL=C sort
) > "$SOURCE_PATHS"
(
    cd "$EXTRACTED_APP"
    find . -print | LC_ALL=C sort
) > "$EXTRACTED_PATHS"
diff -u "$SOURCE_PATHS" "$EXTRACTED_PATHS" \
    || fail "bundle path listing differs; refusing to remove source app"

SOURCE_SHA=$(shasum -a 256 "$APP_PATH/Contents/MacOS/Voice Memos Exporter" | awk '{print $1}')
EXTRACTED_SHA=$(shasum -a 256 "$EXTRACTED_APP/Contents/MacOS/Voice Memos Exporter" | awk '{print $1}')
[ "$SOURCE_SHA" = "$EXTRACTED_SHA" ] \
    || fail "main executable SHA-256 differs after expansion"

echo "Run bundled selftest (120 second timeout)"
if ! /usr/bin/python3 - "$EXTRACTED_APP/Contents/MacOS/Voice Memos Exporter" <<'PY'
import json
import os
import subprocess
import sys

environment = os.environ.copy()
environment["VMX_APP_SELFTEST"] = "1"
try:
    result = subprocess.run(
        [sys.argv[1]], capture_output=True, text=True, timeout=120, env=environment
    )
except subprocess.TimeoutExpired:
    print("selftest timed out after 120 seconds", file=sys.stderr)
    raise SystemExit(1)
if result.returncode != 0:
    print(result.stderr, file=sys.stderr, end="")
    raise SystemExit(result.returncode or 1)
try:
    payload = json.loads(result.stdout)
except json.JSONDecodeError as error:
    print(f"selftest did not produce JSON: {error}", file=sys.stderr)
    raise SystemExit(1)
if payload.get("frozen") is not True or payload.get("vmx_core_ok") is not True:
    print("selftest JSON is missing frozen=true or vmx_core_ok=true", file=sys.stderr)
    raise SystemExit(1)
PY
then
    fail "bundled selftest failed; source app and ZIP were retained"
fi

echo "Verification passed; removing source bundle: $APP_PATH"
rm -rf "$APP_PATH"
echo "Package complete: $ZIP_PATH"
