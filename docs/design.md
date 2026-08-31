# Design and implementation notes

[日本語版: design-ja.md](design-ja.md)

Internal architecture and implementation details for this fork. For CLI behavior, see [usage.md](usage.md).

## Architecture

```text
Voice Memos DB / files
        ↓
    vmx_core.py
        ↓
        ├── export_voice_memos.py (CLI)
        └── voice_memos_exporter.py (Tkinter GUI / PyInstaller .app)
```

`vmx_core.py` is the single export engine and reliability boundary: it diagnoses and reads the database, resolves sources, generates safe destinations, exports, and writes diagnostics. Two supported front ends call that core: `export_voice_memos.py` provides the command-line interface, while `voice_memos_exporter.py` provides the Tkinter GUI and is also shipped as a PyInstaller `.app`. The GUI calls the `vmx_core` API directly; it never parses CLI stdout and never shells out to the CLI.

## Why this fork exists

The following reproducible failures were identified while auditing the upstream code:

- **`"Item ... not found"` after searching (upstream Issue #7):** selection was stored as Tkinter Treeview item IDs, but filtering deleted and recreated the rows, invalidating those IDs. Tk assigns IDs as sequential `I%03X` values; the reported `I16CD` represents the 5,837th row created in that session. Macs with many recordings reach this failure more easily.
- **A title containing `/` stopped export (upstream Issue #2):** the title was not sanitized, so `os.path.join()` treated `/` as a directory separator.
- **A numeric-only title stopped export:** Tkinter can convert Treeview values such as `2026` to `int`, after which `os.path.basename(int)` raises `TypeError`.

The distributed upstream 1.0.2 binary was built from tag `1.0.2`, before the later per-recording `try/except` change. A single recording failure therefore stopped the entire export.

For the corresponding fixes, see `docs/CHANGELOG.md`.

## Database access

- Identifiers are read from the database rather than from any UI state: `Z_PK`, `ZUNIQUEID`, or `ZPATH`, in that preference order. This is what makes search/filter selection and re-export by source path reliable across upstream Issue #7.
- The recording's source path is loaded once from `ZCLOUDRECORDING.ZPATH` and reused for export; the CLI never re-queries the database by displayed title and date, so recordings with identical titles and timestamps are not confused.
- Recently Deleted (trash) state is read from `ZCLOUDRECORDING.ZEVICTIONDATE`: a non-null value means the recording is trashed. This is the field behind `Recording.is_trashed` and the CLI's `--include-trash` behavior (see [usage.md](usage.md)).
- Recording date (`DATE` in listings, and the basis for `--from`/`--to` comparisons) comes from `ZDATE`, converted with `datetime.fromtimestamp()` into a local naive `datetime`. A date-only `--to` is expanded to `time.max` (`23:59:59.999999`) on that date so the whole day is included.
- The SQLite connection is opened read-only. When WAL handling requires it, the database and its sidecar files are copied to a temporary snapshot, which is removed after reading. The original database and recordings are never modified.
- Database problems are classified as missing, permission denied, unsupported schema, locked, corrupt, or unknown, so the CLI can show Full Disk Access guidance only for permission failures.
- An iCloud placeholder (a sibling `.<name>.icloud` file) is classified as **not downloaded** and skipped with `File not available locally`; the tool never initiates an iCloud download.

## Safe filenames and destinations

`safe_filename()` in `vmx_core.py` makes titles safe for macOS filenames:

- `/`, `\`, and `:` are replaced.
- Control characters and NUL are removed.
- Surrounding spaces and dots are stripped.
- Empty, `.`, and `..` names fall back to a generated name.
- The stem is limited to a maximum UTF-8 byte length (200 bytes) rather than a character count, so multi-byte titles are not corrupted mid-character.

`unique_destination()` avoids overwriting existing files: candidate destinations are checked in order (`name.m4a`, `name_1.m4a`, `name_2.m4a`, ...), and each resolved path is verified to remain inside the chosen export directory (`os.path.realpath` under the export root) before being accepted.

## Partial failure handling

Export processes recordings independently. Each recording resolves to an `Outcome` (exported, skipped, or failed); one failure does not stop the rest. The CLI aggregates these into Total / Exported / Skipped / Failed counts and, when at least one recording was skipped or failed, attempts to write a JSON Lines diagnostic log (see [usage.md](usage.md) for its format and location).

## Timestamps and file format

The tool explicitly sets only modification time (`mtime`) and access time (`atime`) to the recording time from `ZDATE`. It does **not** set or preserve creation time (`birthtime`). On APFS/HFS+, setting an `mtime` earlier than the newly copied file's creation time often causes the filesystem to lower Finder's "Created" date to the same value as a side effect — `os.utime()` is not setting creation time directly, and a recording date later than the copy time does not move creation time forward. This is partial support for upstream Issue #1.

Recordings observed on a real Voice Memos database used a `.qta` extension and a QuickTime container (`ftypqt  `). The exporter preserves the source extension rather than mislabeling its contents; no media conversion is performed.

## Privacy and safety

- No network communication, telemetry, analytics, or data collection.
- Never writes to the Voice Memos database and never renames, deletes, moves, or modifies original recordings.
- Data flow: read the database, read an audio file, copy it to the selected destination. A temporary read snapshot may be used for safe WAL handling and is removed afterward.
- Diagnostic logs are written only to the selected output directory, contain titles and paths but no audio, and are never sent externally.

## Licensing

Upstream `rudrakabir/voice-memos-exporter` publishes an MIT License
(`Copyright (c) 2026 rudrakabir`). This fork adopts the same MIT License and
keeps the upstream copyright line in [LICENSE](../LICENSE), adding a second
copyright line for the fork modifications by Kimiya Kitani. See
[NOTICE](../NOTICE) for the attribution summary.

## Known limitations

- The packaged `.app` is built for Apple Silicon (arm64) only; Intel Macs are not supported or tested, and the bundle is not notarized.
- Intel Mac source execution has not been tested; the CLI/core suite is verified with Python 3.9.6 on Apple Silicon.
- The reader depends on Apple's undocumented internal Voice Memos database schema. Future macOS changes may require updates.
- Exported recordings retain their source extension, including `.qta`; no media conversion is performed.
- Creation time (`birthtime`) is not set or preserved; only `mtime` and `atime` are explicitly set.
- iCloud-only recordings are not downloaded; recognized placeholders are skipped.
