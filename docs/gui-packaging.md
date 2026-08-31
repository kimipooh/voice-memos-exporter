# GUI packaging

[日本語版: gui-packaging-ja.md](gui-packaging-ja.md)

This workflow builds the macOS Voice Memos Exporter app bundle with PyInstaller.

The app is built for Apple Silicon with Homebrew Python 3.14.7 (arm64),
Tcl/Tk 9.0, and PyInstaller 6.22.2. PyInstaller is installed in the
git-ignored `.venv-package` virtual environment.

## App bundle

The app bundle contains Python and Tk, so users do not need Python, Homebrew,
or Tk. It is Apple Silicon (arm64) only; Intel and universal2 builds are not
supported. The main executable is under `Contents/MacOS`, its metadata is in
`Contents/Info.plist`, and bundled libraries are under `Contents/Frameworks`.

Set up the packaging environment with:

```bash
/opt/homebrew/bin/python3.14 -m venv .venv-package && .venv-package/bin/python -m pip install pyinstaller
```

Build the app with:

```bash
bash packaging/build_app.sh
```

The output is `dist/Voice Memos Exporter.app`, with bundle identifier
`jp.kitani.voicememosexporter`.

Run the packaging smoke test as part of the full test suite after building:

```bash
/usr/bin/python3 -m unittest discover -s tests -t .
```

The smoke test runs the bundled selftest with `VMX_APP_SELFTEST=1`, verifies the
bundle layout, identifier, versions, and Tcl/Tk libraries, and uses `otool -L`
to confirm that the executable does not depend on Homebrew, an external Python
framework, or `/usr/bin/python3`. If the app has not been built, the bundle
smoke tests are skipped.

Grant Full Disk Access to `Voice Memos Exporter.app` itself, not Terminal or
another terminal application. Rebuilding changes the bundle's code-signing or
inode identity, so macOS may require the app to be approved again in System
Settings.

The bundle is ad-hoc signed, not signed with an Apple Developer ID certificate,
and not notarized. Gatekeeper therefore blocks the first launch; see
[First launch is blocked](troubleshooting.md#first-launch-is-blocked).

## Release asset

Create the distributable zip with:

```bash
cd dist
ditto -c -k --sequesterRsrc --keepParent \
  "Voice Memos Exporter.app" \
  "Voice-Memos-Exporter-v1.1.0-macOS-arm64.zip"
```

Use `ditto`, not `zip`, so the bundle's symlinks and resource forks survive.
The release ZIP is `dist/Voice-Memos-Exporter-v1.1.0-macOS-arm64.zip`.
