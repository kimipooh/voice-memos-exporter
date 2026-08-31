# Contributing to Voice Memos Exporter

[日本語版: CONTRIBUTING-ja.md](CONTRIBUTING-ja.md)

We love your input! We want to make contributing to Voice Memos Exporter as easy and transparent as possible, whether it is:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development process

We use GitHub to host code, track issues and feature requests, and accept pull requests.

1. Fork the repository and create your branch from `main`.
2. If you have added code that should be tested, add tests.
3. If you have changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints.
6. Open the pull request.

## Development environment

- Clone the repository.
- For general development, create and activate a virtual environment with
  `python3 -m venv venv` and `source venv/bin/activate`.
- Development requires macOS.
- The CLI supports Python 3.9 or later.
- GUI and packaging verification use Python 3.14.7 and Tcl/Tk 9.0.
- Packaging uses the external `~/.venvs/voice-memos-exporter/package` virtual environment by default. Create it with `/opt/homebrew/bin/python3.14 -m venv "$HOME/.venvs/voice-memos-exporter/package"`, then install PyInstaller as described in [gui-packaging.md](gui-packaging.md). Set `VMX_PACKAGE_VENV` only to make `build_app.sh` use a different packaging virtual environment; see [gui-packaging.md](gui-packaging.md) for setup and build commands.

## Running tests

Run the repository's test suite with:

```bash
/usr/bin/python3 -m unittest discover -s tests -t .
```

Do not weaken or skip tests to make a change pass.

## Checking the CLI

```bash
python3 export_voice_memos.py --help
python3 export_voice_memos.py --version
```

## GUI tests

Some GUI tests require Tk. They cannot run in an environment that cannot connect to macOS WindowServer. Run the GUI from source with `python3 voice_memos_exporter.py` when checking the interface manually.

## Packaging tests

The packaging smoke tests are skipped when `dist/Voice Memos Exporter.app` has not been built. After building the app, the same test-suite command runs them and verifies the bundle selftest, layout, metadata, bundled Tcl/Tk, and external dependencies.

## Building

Build the app with:

```bash
bash packaging/build_app.sh
```

See [gui-packaging.md](gui-packaging.md) for the packaging environment, validation, and release ZIP command.

## Manual tests

The following checks require a real Voice Memos database and cannot be fully automated: list display, export, dry run, Recently Deleted, cancellation, titles containing `/`, numeric-only titles, iCloud-only recordings, confirmation that the original database is unchanged, Gatekeeper approval, and Full Disk Access.

Use the complete [GUI manual test checklist](gui-notes.md#manual-test-checklist).

## Contribution policy

- `vmx_core.py` is the source of truth for database and export logic.
- Do not create a separate export engine in the GUI.
- Never modify the original Voice Memos database or recordings.
- Do not regress the CLI or weaken the tests.
- Preserve upstream attribution and the MIT License.
- Keep `README.md` and `README-ja.md`, and English/Japanese document pairs, in sync.

## License

This project is licensed under the MIT License; see [LICENSE](../LICENSE).
The upstream project `rudrakabir/voice-memos-exporter` publishes the same MIT
License. By contributing, you agree that your contributions are licensed under
the MIT License.
