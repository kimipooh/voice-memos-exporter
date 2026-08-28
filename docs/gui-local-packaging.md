# GUI local packaging

This packaging workflow is local-only. Do not publish, redistribute, or release
the resulting app. The upstream license status remains unresolved.

The app is built for Apple Silicon with Homebrew Python 3.14.7 (arm64),
Tcl/Tk 9.0, and PyInstaller 6.22.2. PyInstaller is installed in the
git-ignored `.venv-package` virtual environment.

Set up the packaging environment with:

```bash
/opt/homebrew/bin/python3.14 -m venv .venv-package && .venv-package/bin/python -m pip install pyinstaller
```

Build the app with:

```bash
bash packaging/build_local_app.sh
```

The output is `dist/Voice Memos Exporter.app`, with bundle identifier
`jp.kitani.voicememosexporter.local`.

Run the packaging smoke test as part of the full test suite after building:

```bash
/usr/bin/python3 -m unittest discover -s tests -t .
```

Grant Full Disk Access to `Voice Memos Exporter.app` itself, not Terminal or
another terminal application. Rebuilding changes the bundle's code-signing or
inode identity, so macOS may require the app to be approved again in System
Settings.

`README.md`, `README-ja.md`, and `NOTICE` are intentionally unchanged by this
packaging work.
