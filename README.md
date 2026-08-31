# Voice Memos Exporter

[Japanese: README-ja.md](README-ja.md)

This is a fork of [rudrakabir/voice-memos-exporter](https://github.com/rudrakabir/voice-memos-exporter), created by [rudrakabir](https://github.com/rudrakabir). Thank you to the original author for publishing a useful tool for bulk exporting macOS Voice Memos.

This fork revisits cases where some recordings could fail to export in certain environments, adds support for current macOS, and adds a command-line interface. Voice Memos can now be exported from either the GUI app or the Python CLI.

## Features

- Export all recordings, or filter by title and/or date range, to a folder you choose.
- GUI list with Title / Date / Duration / Local / Status, title search, and Include Recently Deleted.
- Select All / Deselect All, dry-run preview, export progress, and cancellation in the GUI.
- Continues past individual failures and reports Total / Exported / Skipped / Failed.
- Generates safe filenames automatically, including titles containing `/` and numeric-only titles.
- Reads the Voice Memos database read-only, never modifies the originals, and makes no network access.

## Quick Start (GUI app)

The GUI app is self-contained — no Python, Homebrew, or Tcl/Tk needed.

1. Download `Voice-Memos-Exporter-v1.1.0-macOS-arm64.zip` from the GitHub Releases page.
2. Unzip it and move `Voice Memos Exporter.app` to `/Applications`.
3. Open the app once.
4. If macOS blocks it, open System Settings → Privacy & Security, go to Security, click **Open**, then **Open Anyway**, and enter your login password. The app is not notarized, so Gatekeeper blocks the first launch — see [First launch is blocked](docs/troubleshooting.md#first-launch-is-blocked).
5. Open the app again.
6. When the app asks for Full Disk Access, open System Settings → Privacy & Security → Full Disk Access, add `Voice Memos Exporter.app`, and turn it on. This is a separate permission from step 4 — see [Full Disk Access](docs/troubleshooting.md#full-disk-access-is-required).
7. Quit the app completely and reopen it.
8. Select the recordings you want, or use Select All.
9. Choose an output folder and click **Export Selected**. Use **Dry run** first to preview without writing anything.

## Quick Start (CLI)

```bash
python3 export_voice_memos.py --help
python3 export_voice_memos.py --list
python3 export_voice_memos.py --all --output ~/Desktop/voice-memos-export
```

Example — export a date range:

```bash
python3 export_voice_memos.py \
  --all \
  --from 2026-07-01 \
  --to 2026-07-31 \
  --output ~/Desktop/voice-memos-export
```

`--list`, `--all`, and `--search` are the three modes; at least one is required. See [docs/usage.md](docs/usage.md) for all options and examples.

## Requirements

### GUI app

- macOS on Apple Silicon (arm64).
- Self-contained: no Python, Homebrew, or Tcl/Tk required.
- Full Disk Access for `Voice Memos Exporter.app` itself.

### CLI

- macOS with Voice Memos data in its default location.
- Python 3.9 or later; the CLI uses only the Python standard library.
- Full Disk Access for the terminal application that runs Python.

## Supported environments

| | GUI app | CLI |
|---|---|---|
| macOS | Verified on macOS 26.6.2; earlier versions untested | Verified on macOS 26.6.2; earlier versions untested |
| Architecture | Apple Silicon (arm64) only | Apple Silicon (arm64) verified |
| Intel (x86_64) | Not supported, not tested | Not tested |
| Python required | No (bundled) | Yes, 3.9 or later |
| Full Disk Access granted to | `Voice Memos Exporter.app` | the terminal application |

## Common issues

- **The app will not open on first launch** (only "Move to Trash" / "Done" shown): Gatekeeper blocks it because the app is not notarized. Allow it in System Settings → Privacy & Security. See [First launch is blocked](docs/troubleshooting.md#first-launch-is-blocked).
- **`Voice Memos database not found`**: usually means the Voice Memos database has not been created yet — open Apple's Voice Memos app once and confirm you have recordings on this Mac. See [Voice Memos database not found](docs/troubleshooting.md#voice-memos-database-not-found).

For anything else, see [docs/troubleshooting.md](docs/troubleshooting.md).

## Notes and limitations

- Recently Deleted recordings are excluded by default; use `--include-trash` to include them.
- A date-only `--to` includes the entire day.
- The reader depends on Apple's undocumented internal Voice Memos database schema, so a future macOS change could require an update.
- Exported files keep their source extension (some recordings use `.qta`); no media conversion is performed.
- iCloud-only recordings are not downloaded; they are listed and skipped as unavailable locally.
- The app is built for Apple Silicon only; Intel Macs are neither supported nor tested.
- The app is not notarized.

## Documentation

| Topic | English | 日本語 |
|---|---|---|
| CLI reference | [usage.md](docs/usage.md) | [usage-ja.md](docs/usage-ja.md) |
| Troubleshooting | [troubleshooting.md](docs/troubleshooting.md) | [troubleshooting-ja.md](docs/troubleshooting-ja.md) |
| Architecture and design | [design.md](docs/design.md) | [design-ja.md](docs/design-ja.md) |
| Building the app bundle | [gui-packaging.md](docs/gui-packaging.md) | [gui-packaging-ja.md](docs/gui-packaging-ja.md) |
| Change history | [CHANGELOG.md](docs/CHANGELOG.md) | [CHANGELOG-ja.md](docs/CHANGELOG-ja.md) |
| Contributing and tests | [CONTRIBUTING.md](docs/CONTRIBUTING.md) | [CONTRIBUTING-ja.md](docs/CONTRIBUTING-ja.md) |

[docs/gui-notes.md](docs/gui-notes.md) covers GUI behavior and the manual test checklist (English only).

## Upstream and acknowledgements

Original work © rudrakabir — https://github.com/rudrakabir/voice-memos-exporter

If the original project is useful to you, consider supporting its author:<br>
☕ [Buy Me a Coffee](https://www.buymeacoffee.com/rudrakabir)

## License

MIT License. See [LICENSE](LICENSE).

- Original work © 2026 rudrakabir
- Fork modifications © 2026 Kimiya Kitani

See [NOTICE](NOTICE) for attribution details.
