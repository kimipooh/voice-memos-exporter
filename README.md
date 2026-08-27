# Voice Memos Exporter

[日本語版: README-ja.md](README-ja.md)

This is a development fork of [rudrakabir/voice-memos-exporter](https://github.com/rudrakabir/voice-memos-exporter), created by [rudrakabir](https://github.com/rudrakabir). The original project made it possible to bulk export macOS Voice Memos, and this fork is grateful to the original author for that useful work. This fork focuses on reliable bulk export of macOS Voice Memos through a Python command-line interface.

The upstream license is currently unclear, so this fork is not offered as an independent release or binary distribution; see [Notes and limitations](#notes-and-limitations).

## Features

- Exports all recordings, or a subset filtered by title and/or date range, to a folder you choose.
- Continues past individual failures and reports Total / Exported / Skipped / Failed instead of stopping the whole export.
- Generates safe filenames automatically, including for titles with `/` or numeric-only titles that broke the original tool.
- Reads the Voice Memos database read-only and never modifies the originals.
- No network access, telemetry, or data collection.

## Requirements

- macOS with Voice Memos data in its default location.
- Python 3.9 or later. The CLI uses only the Python standard library — no third-party dependencies.
- Full Disk Access for the terminal application that runs Python.

### Full Disk Access

Voice Memos data is protected by macOS privacy controls. Grant Full Disk Access (System Settings → Privacy & Security) to the terminal application that actually starts Python — Terminal, iTerm, or an IDE's integrated terminal — then restart it. If access is missing, the CLI prints guidance and exits with status 1.

## Quick Start

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
- The upstream repository does not currently provide a clear LICENSE file, so this fork does not make an independent license claim and is not offered as a release or binary distribution.

## Documentation

- [docs/usage.md](docs/usage.md) — full CLI reference and behavior details
- [docs/design.md](docs/design.md) — architecture and internal implementation notes
- [docs/CHANGELOG.md](docs/CHANGELOG.md) — change history
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) — contributing and running tests

## Upstream and acknowledgements

Original work © rudrakabir — https://github.com/rudrakabir/voice-memos-exporter

If the original project is useful to you, consider supporting its author:<br>
☕ [Buy Me a Coffee](https://www.buymeacoffee.com/rudrakabir)
