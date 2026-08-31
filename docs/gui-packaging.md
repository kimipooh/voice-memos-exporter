# GUI packaging

This workflow builds the macOS Voice Memos Exporter app bundle with PyInstaller.

The app is built for Apple Silicon with Homebrew Python 3.14.7 (arm64),
Tcl/Tk 9.0, and PyInstaller 6.22.2. PyInstaller is installed in the
git-ignored `.venv-package` virtual environment.

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

Grant Full Disk Access to `Voice Memos Exporter.app` itself, not Terminal or
another terminal application. Rebuilding changes the bundle's code-signing or
inode identity, so macOS may require the app to be approved again in System
Settings.

## Release asset

Create the distributable zip with:

```bash
cd dist
ditto -c -k --sequesterRsrc --keepParent \
  "Voice Memos Exporter.app" \
  "Voice-Memos-Exporter-v1.1.0-macOS-arm64.zip"
```

Use `ditto`, not `zip`, so the bundle's symlinks and resource forks survive.
The app is unsigned and not notarized.
