# CLI usage

[日本語版: usage-ja.md](usage-ja.md)

Full reference for `export_voice_memos.py`. For a quick start, see the root [README.md](../README.md).

## Modes

At least one of `--list`, `--all`, or `--search` is required.

- `--list` lists recordings without exporting. `--list --search TEXT` lists only matches.
- Without `--list`, `--all` or `--search` performs an export and requires `--output`.

## Options

| Option | Meaning |
|---|---|
| `-h`, `--help` | Show help and exit. |
| `--list` | List recordings without exporting. |
| `--all` | Export all recordings. |
| `--search TEXT` | Filter titles by case-insensitive substring, with Unicode normalization. |
| `--from DATE` | Include recordings on or after `DATE`. |
| `--to DATE` | Include recordings on or before `DATE`. A date without a time includes the entire day. |
| `--output DIR`, `-o DIR` | Export destination directory. |
| `--dry-run` | Resolve sources and destinations and show results without writing export files, logs, or the output directory. |
| `--json` | Write `--list` output as one JSON array. |
| `--include-trash` | Include recordings in Recently Deleted. Text listings add a `STATUS` column. |
| `--db PATH` | Override the Voice Memos database path. |
| `--no-set-times` | Do not set exported file `mtime` and `atime`. |
| `--version` | Print the tool version and exit. |

`--from`/`--to`, `--all`/`--search`/`--list`, `--include-trash`, `--dry-run`, and `--json` all combine freely. Title and date filters use AND logic.

## Date filtering

Accepted formats for `--from` and `--to`:

- `YYYY-MM-DD`
- `YYYY-MM-DD HH:MM`
- `YYYY-MM-DD HH:MM:SS`

Both bounds are inclusive and may be specified independently. A date-only `--to` includes the entire day (internally treated as `23:59:59.999999` on that date). Input dates are interpreted in local time, matching the `DATE` column that the CLI derives from each recording and shows in `--list`.

Example — recordings from July 2026 only:

```bash
python3 export_voice_memos.py \
  --all \
  --from 2026-07-01 \
  --to 2026-07-31 \
  --output ~/Desktop/voice-memos-export
```

For how the local `DATE` value is derived from the database, see [design.md](design.md).

## Examples

Include recordings in Recently Deleted:

```bash
python3 export_voice_memos.py --all --include-trash --output ~/Desktop/voice-memos-export
```

Preview an export without writing anything:

```bash
python3 export_voice_memos.py --all --dry-run --output ~/Desktop/voice-memos-export
```

## Recently Deleted (trash)

By default, recordings in Recently Deleted are excluded from listing, searching, dry runs, and export. Add `--include-trash` to include them. Text listings then add a `STATUS` column; JSON objects always include an additive `status` field (`active` or `trash`).

For which database field this is detected from, see [design.md](design.md).

## List output

Text output uses the following format (the titles below are fictional):

```text
Total recordings: 3 (matched: 2)
KEY                DATE             DURATION LOCAL   TITLE
pk:101             2026-08-27 10:00     0:42 yes     Project kickoff
pk:102             2026-08-26 15:30  1:02:03 icloud  Project interview
```

`LOCAL` distinguishes three states:

| Value | Meaning |
|---|---|
| `yes` | The audio file is available locally. |
| `icloud` | An iCloud placeholder exists, but the recording is not downloaded locally. Export skips it. |
| `missing` | The database row exists, but neither a local file nor an iCloud placeholder was found. Export treats it as a failure and continues. |

With `--json`, stdout is only a JSON array. A zero-match `--list --json --search TEXT` returns `[]` with exit code 0.

## Export output and diagnostics

Export prints one result per recording, followed by Total, Exported, Skipped, and Failed counts. `--dry-run` prefixes result lines with `[dry-run]`, reports successful candidates as `would export`, and writes nothing: no audio file, diagnostic log, or output directory.

For a real export, the tool attempts to create a diagnostic log in the output directory only when at least one item is skipped or fails. If log creation succeeds, its path is printed. The log is JSON Lines, one record per skipped/failed recording, with the recording identifier, title, source path, destination path, outcome, exception type, and exception message. It can contain private titles and paths but never the audio itself, and it is never transmitted anywhere.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success. This includes a successful `--list` with zero search matches, or an export with no skipped or failed recordings. |
| `1` | Fatal error: invalid arguments, database/output error, zero search matches during export, or interruption. |
| `2` | Export completed with one or more skipped or failed recordings. |

## Development and testing

See [CONTRIBUTING.md](CONTRIBUTING.md) for running the test suite locally.
