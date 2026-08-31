# Voice Memos Exporter

[Japanese: README-ja.md](README-ja.md)

This is a development fork of [rudrakabir/voice-memos-exporter](https://github.com/rudrakabir/voice-memos-exporter), created by [rudrakabir](https://github.com/rudrakabir). The original project made it possible to bulk export macOS Voice Memos, and this fork is grateful to the original author for that useful work. This fork focuses on reliable bulk export of macOS Voice Memos through both a GUI app and a Python command-line interface.

This fork provides two front ends over one shared export core: a macOS GUI
application and a Python command-line interface. Both are MIT licensed.

## Features

- Exports all recordings, or a subset filtered by title and/or date range, to a folder you choose.
- Provides a GUI recording list with Title / Date / Duration / Local / Status columns, title search, and an "Include Recently Deleted" option.
- Supports Select All / Deselect All and dry-run previews in the GUI.
- Shows GUI export progress with cancellation support.
- Reports a final Total / Exported / Skipped / Failed summary in both front ends.
- Continues past individual failures and reports Total / Exported / Skipped / Failed instead of stopping the whole export.
- Generates safe filenames automatically, including for titles with `/` or numeric-only titles that broke the original tool.
- Reads the Voice Memos database read-only and never modifies the originals.
- No network access, telemetry, or data collection.

## Quick Start (GUI app)

The GUI app is self-contained. You do not need Python, Homebrew, or Tcl/Tk.

1. Download `Voice-Memos-Exporter-v1.1.0-macOS-arm64.zip` from the GitHub
   Releases page and unzip it.
2. Move `Voice Memos Exporter.app` to `/Applications`.
3. Open it once. macOS will report that it cannot read the Voice Memos data.
4. Open System Settings → Privacy & Security → Full Disk Access, click `+`,
   and add `Voice Memos Exporter.app`. Make sure its switch is on.
5. Quit and reopen the app.
6. Select the recordings you want, or use Select All.
7. Choose an output folder and click **Export Selected**. Use **Dry run** first
   if you want to preview without writing anything.

The app is not notarized, so on first launch macOS may require you to allow it
from System Settings → Privacy & Security.

## Requirements

### GUI app

- macOS on Apple Silicon (arm64).
- Self-contained: no Python, Homebrew, or Tcl/Tk required.
- Full Disk Access for `Voice Memos Exporter.app` itself.

### CLI

- macOS with Voice Memos data in its default location.
- Python 3.9 or later. The CLI uses only the Python standard library — no third-party dependencies.
- Full Disk Access for the terminal application that runs Python.

### Full Disk Access

Voice Memos data is protected by macOS privacy controls. Grant Full Disk Access (System Settings → Privacy & Security) to the terminal application that actually starts Python — Terminal, iTerm, or an IDE's integrated terminal — then restart it. If access is missing, the CLI prints guidance and exits with status 1.

## Supported environments

| | GUI app | CLI |
|---|---|---|
| macOS | Verified on macOS 26.6.2; earlier versions untested | Verified on macOS 26.6.2; earlier versions untested |
| Architecture | Apple Silicon (arm64) only | Apple Silicon (arm64) verified |
| Intel (x86_64) | Not supported, not tested | Not tested |
| Python required | No (bundled) | Yes, 3.9 or later |
| Full Disk Access granted to | `Voice Memos Exporter.app` | the terminal application |

## Quick Start (CLI)

```bash
python3 export_voice_memos.py --help
python3 export_voice_memos.py --list
python3 export_voice_memos.py --all --output ~/Desktop/voice-memos-export
```

## Common Examples

Export a date range:

```bash
python3 export_voice_memos.py \
  --all \
  --from 2026-07-01 \
  --to 2026-07-31 \
  --output ~/Desktop/voice-memos-export
```

Include recordings in Recently Deleted:

```bash
python3 export_voice_memos.py \
  --all \
  --include-trash \
  --output ~/Desktop/voice-memos-export
```

Preview an export without writing anything:

```bash
python3 export_voice_memos.py --all --dry-run --output ~/Desktop/voice-memos-export
```

## Main Options

| Option | Meaning |
|---|---|
| `--list` | List recordings without exporting. |
| `--all` | Export all recordings. |
| `--search TEXT` | Filter titles by case-insensitive substring. |
| `--from DATE`, `--to DATE` | Filter by recording date (`YYYY-MM-DD[ HH:MM[:SS]]`). |
| `--include-trash` | Include Recently Deleted recordings. |
| `--dry-run` | Show what would be exported without writing anything. |
| `--json` | Write `--list` output as JSON. |
| `--output DIR`, `-o DIR` | Export destination directory. |

`--list`, `--all`, and `--search` are the three modes; at least one is required. See [docs/usage.md](docs/usage.md) for the full option reference, list/export output formats, and exit codes.

## Notes and limitations

- Recently Deleted recordings are excluded by default; use `--include-trash` to include them.
- A date-only `--to` includes the entire day.
- The reader depends on Apple's undocumented internal Voice Memos database schema, so a future macOS change could require an update.
- Exported files keep their source extension (some recordings use `.qta`); no media conversion is performed.
- iCloud-only recordings are not downloaded; they are listed/skipped as not available locally.
- The app is built for Apple Silicon only; Intel Macs are neither supported nor tested.
- The app is not notarized.

## Documentation

- [docs/usage.md](docs/usage.md) — full CLI reference and behavior details
- [docs/design.md](docs/design.md) — architecture and internal implementation notes
- [docs/gui-notes.md](docs/gui-notes.md) — GUI behavior and manual test checklist
- [docs/gui-packaging.md](docs/gui-packaging.md) — building the app bundle
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — change history
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) — contributing and running tests

## Upstream and acknowledgements

Original work © rudrakabir — https://github.com/rudrakabir/voice-memos-exporter

If the original project is useful to you, consider supporting its author:<br>
☕ [Buy Me a Coffee](https://www.buymeacoffee.com/rudrakabir)

## License

MIT License. See [LICENSE](LICENSE).

- Original work © 2026 rudrakabir
- Fork modifications © 2026 Kimiya Kitani

See [NOTICE](NOTICE) for attribution details.
