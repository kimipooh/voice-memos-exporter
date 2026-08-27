# Voice Memos Exporter

[日本語版: README-ja.md](README-ja.md)

<p align="center">
  <img src="app_icon.png" alt="Voice Memos Exporter Icon" width="128" height="128">
</p>

This is a development fork of [rudrakabir/voice-memos-exporter](https://github.com/rudrakabir/voice-memos-exporter), created by [rudrakabir](https://github.com/rudrakabir). Thanks to the original author for building a useful bulk exporter for macOS Voice Memos. This fork focuses on reliable exports and supported Python command-line and graphical interfaces.

The upstream license is currently unclear. This fork is not offered as an independent release or binary distribution; see [License](#license).

<p align="center">
  <img src="screenshot.png" alt="Voice Memos Exporter Screenshot" width="800">
</p>

If the original project is useful to you, consider supporting its author:<br>
☕ [Buy Me a Coffee](https://www.buymeacoffee.com/rudrakabir)

## Why this fork exists

The following reproducible failures were identified while auditing the upstream code:

- **`"Item ... not found"` after searching (upstream Issue #7):** selection was stored as Tkinter Treeview item IDs, but filtering deleted and recreated the rows, invalidating those IDs. Tk assigns IDs as sequential `I%03X` values; the reported `I16CD` represents the 5,837th row created in that session. Macs with many recordings reach this failure more easily.
- **A title containing `/` stopped export (upstream Issue #2):** the title was not sanitized, so `os.path.join()` treated `/` as a directory separator.
- **A numeric-only title stopped export:** Tkinter can convert Treeview values such as `2026` to `int`, after which `os.path.basename(int)` raises `TypeError`.

The distributed upstream 1.0.2 binary was built from tag `1.0.2`, before the later per-recording `try/except` change. A single recording failure therefore stopped the entire export.

## What changed

- Selection is stored with stable database-derived identifiers (`Z_PK`, `ZUNIQUEID`, or `ZPATH`), so searching and filtering do not invalidate it.
- Export uses the source path loaded with each recording instead of querying the database again by displayed title and date. Recordings with identical titles and timestamps are not confused.
- Filenames are made safe for macOS: `/`, `\`, and `:` are replaced; control characters and NUL are removed; surrounding spaces and dots are stripped; empty, `.`, and `..` names get fallbacks; and stems are limited by UTF-8 byte length. Existing names are preserved with suffixes such as `name_1.m4a`.
- Every destination is checked to remain inside the chosen export directory.
- One recording failure no longer stops the rest. The result reports **Total / Exported / Skipped / Failed**.
- A diagnostic log named `voice-memos-exporter-YYYYMMDD-HHMMSS.log` is attempted when at least one recording is skipped or fails.
- The SQLite database is opened read-only. When needed for WAL handling, the database and sidecar files are copied to a temporary snapshot and the snapshot is removed after reading.
- Database problems are classified as missing, permission denied, unsupported schema, locked, corrupt, or unknown. Full Disk Access guidance is used only for permission failures.
- An iCloud placeholder is classified as **not downloaded** and skipped with `File not available locally`; the tool does not initiate an iCloud download.
- GUI copying runs on a worker thread and provides progress plus **Cancel**.
- Export explicitly sets modification time (`mtime`) and access time (`atime`) from the recording's `ZDATE` (partial support for upstream Issue #1).
- Shared logic lives in `vmx_core.py`, with regression tests for the core, CLI, and GUI selection behavior.
- The PyInstaller spec requests `target_arch='universal2'` (upstream Issue #4), but that build has not been verified.
- Both the CLI and GUI display recording counts (upstream Issue #3).

## Requirements and compatibility

- macOS with Voice Memos data under `~/Library/Group Containers/group.com.apple.VoiceMemos.shared/`. The optional app spec declares macOS 12.0 as its minimum.
- Python 3 with the standard library. Runtime use does not require packages from `requirements.txt`; its `pyinstaller` entry is only for building the optional app.
- Full Disk Access for the process that reads the Voice Memos database.

### Python source compatibility

The source uses only the Python standard library and contains no architecture-dependent code. It has been verified on Apple Silicon. The same source is expected to run on Intel Macs, but no Intel Mac has been tested.

### Prebuilt app compatibility

The app distributed by upstream is Apple Silicon-only (upstream Issue #4). This fork answers that limitation by providing direct Python source execution. Its `.spec` now specifies `target_arch='universal2'`, but a Universal 2 build has not been verified. Building one requires a Universal 2 Python, such as the python.org macOS universal2 installer; a single-architecture Homebrew Python cannot produce that bundle.

## Full Disk Access

Voice Memos data is protected by macOS TCC and requires Full Disk Access. Permission must be granted to the process that actually accesses the database:

- For the Python CLI or GUI started from source, grant access to the terminal application that starts Python, such as Terminal.app, iTerm2, or the VS Code application hosting its integrated terminal. Do not add the `python3` binary by itself.
- For a packaged `.app`, grant access to the `.app` itself.

Open **System Settings → Privacy & Security → Full Disk Access**, add and enable the applicable application, and then **restart that application** so the change takes effect.

The database is still opened read-only. If the CLI detects `DbStatus.PERMISSION_DENIED`, it prints Full Disk Access guidance and exits with status 1. Missing databases and unsupported schemas receive different diagnostics.

## Command line (recommended)

The CLI is the recommended, formally supported interface.

```bash
python3 export_voice_memos.py --help
python3 export_voice_memos.py --list
python3 export_voice_memos.py --list --include-trash
python3 export_voice_memos.py --list --search "Project"
python3 export_voice_memos.py --all --output ~/Desktop/VoiceMemos
python3 export_voice_memos.py --search "Project" --output ~/Desktop/VoiceMemos
python3 export_voice_memos.py --all --dry-run --output ~/Desktop/VoiceMemos
```

At least one of `--list`, `--all`, or `--search` is required. `--list --search TEXT` lists only matches; without `--list`, `--all` or `--search` performs an export and requires `--output`.

By default, recordings in Recently Deleted are excluded from listing, searching, dry runs, and export. Add `--include-trash` to include them. The GUI also excludes them by default.

| Option | Meaning |
|---|---|
| `-h`, `--help` | Show help and exit. |
| `--list` | List recordings without exporting. |
| `--all` | Export all recordings. |
| `--search TEXT` | Filter titles by case-insensitive substring, with Unicode normalization. |
| `--output DIR`, `-o DIR` | Export destination directory. |
| `--dry-run` | Resolve sources and destinations and show results without writing export files, logs, or the output directory. |
| `--json` | Write `--list` output as one JSON array. |
| `--include-trash` | Include recordings in Recently Deleted. Text listings add a `STATUS` column. |
| `--db PATH` | Override the Voice Memos database path. |
| `--no-set-times` | Do not set exported file `mtime` and `atime`. |
| `--version` | Print the tool version and exit. |

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Success. This includes a successful `--list` with zero search matches, or an export with no skipped or failed recordings. |
| `1` | Fatal error: invalid arguments, database/output error, zero search matches during export, or interruption. |
| `2` | Export completed with one or more skipped or failed recordings. |

### List output

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
| `icloud` | An iCloud placeholder exists, but the recording is not downloaded locally. This is not called `missing`; export skips it. |
| `missing` | The database row exists, but neither a local file nor an iCloud placeholder was found. Export treats it as a failure and continues. |

With `--json`, stdout is only a JSON array. A zero-match `--list --json --search TEXT` returns `[]` with exit code 0.
Each recording object includes an additive `status` field whose value is `active` or `trash`.
With `--include-trash`, text output adds a `STATUS` column with the same values; the default text layout is unchanged.

### Export output and diagnostics

Export prints one result per recording followed by Total, Exported, Skipped, and Failed counts. `--dry-run` prefixes result lines with `[dry-run]`, reports successful candidates as `would export`, and writes no export file of any kind: no audio, diagnostic log, or output directory. As with listing and real export, safe read-only WAL handling may create a temporary database snapshot, which is removed when reading finishes.

For a real export, the tool attempts to create a diagnostic log in the selected output directory only when at least one item is skipped or fails. If log creation succeeds, its path is printed. Each JSON-lines record includes the recording identifier, title, source path, destination path, outcome, exception type, and exception message. The log can therefore contain private titles and paths, but it never contains the audio itself and is not transmitted anywhere.

## Graphical interface

The existing Tkinter GUI remains a formally supported interface:

```bash
python3 voice_memos_exporter.py
```

It supports search, stable selection across filtering, Select All/Deselect All, progress, cancellation, and per-recording result handling. The GUI and CLI both call the same export implementation in `vmx_core.py`.

## Architecture

```text
Voice Memos DB / files
        ↓
    vmx_core.py
        ↓
   ┌────┴────┐
  CLI       GUI
```

`vmx_core.py` is the reliability boundary: it diagnoses and reads the database, resolves sources, generates safe destinations, exports, and writes diagnostics. The CLI and GUI are presentation layers over that shared behavior.

## Exported file metadata and format

The tool explicitly sets only modification time (`mtime`) and access time (`atime`) to the recording time from `ZDATE`. It does **not** set or preserve creation time (`birthtime`). On APFS/HFS+, setting an `mtime` earlier than the newly copied file's creation time often causes the filesystem to lower Finder's “Created” date to the same value as a side effect. `os.utime()` is not setting creation time, and a recording date later than the copy time does not move creation time forward. Recording dates remain visible in export logs and `--list`. This is partial support for upstream Issue #1.

Recordings observed on a real Voice Memos database used a `.qta` extension and a QuickTime container (`ftypqt  `). The exporter preserves the source extension rather than mislabeling its contents. Convert the exported file separately if a player cannot open `.qta`.

## Privacy and safety

- The tool performs no network communication, telemetry, analytics, or data collection.
- It never writes to the Voice Memos database and never renames, deletes, moves, or modifies original recordings.
- Its data flow is: read the database, read an audio file, and copy it to the selected destination. A temporary read snapshot may be used for safe WAL handling and is removed afterward.
- Diagnostic logs are written only to the selected output directory, contain titles and paths but no audio, and are never sent externally.

## Optional `.app` build

The PyInstaller spec remains available as an optional, auxiliary packaging path:

```bash
python3 -m pip install -r requirements.txt
pyinstaller voice_memos_exporter.spec
```

The spec requests Universal 2. Building and running an app remains environment-dependent because of Python architecture, Apple Silicon/Intel targeting, code signing, notarization, Gatekeeper, and which process receives Full Disk Access. No `.app` build was required or verified for this fork documentation work, and no fork Release is available.

## Development and tests

```bash
python3 -m unittest discover -s tests -t .
```

The test suite uses `unittest` from the standard library; pytest is not required.

Measured on 2026-08-27 (macOS 26, Apple Silicon):

| Python | Result |
|---|---|
| `/usr/bin/python3` (Tkinter available) | 49 tests, **OK**, no skips |
| Homebrew `python@3.12` (no `_tkinter`) | 49 tests, **OK (skipped=1)** |

The single skip is the GUI selection test. It skips whenever Tkinter cannot be used — either the Python build ships no `_tkinter` module (Homebrew Python does not) or no display can be connected. Every non-GUI test runs in both cases.

## Known limitations

- The upstream license is unresolved, so this fork has no Release or binary distribution.
- Intel Mac source execution and Universal 2 app builds have not been tested.
- Exported recordings retain their source extension, including `.qta`; no media conversion is performed.
- Creation time (`birthtime`) is not set or preserved; only `mtime` and `atime` are explicitly set.
- iCloud-only recordings are not downloaded. Recognized placeholders are skipped.
- A future macOS Voice Memos schema change may become incompatible with the current reader.

## License

The upstream project does not include a `LICENSE` file, and GitHub reports no license for it. The only reference to a license is in `docs/CONTRIBUTING.md`, which states that contributions are licensed “under its MIT License” — but no MIT license text is present in the repository.

Because of that, the licensing of this code is **unclear**. This fork therefore:

- adds no `LICENSE` file of its own, since it has no authority to license the original author's work;
- is **not** published as an independent release or binary distribution;
- exists as a development fork for personal use and as a basis for contributing fixes back upstream.

An [issue draft](docs/audit/upstream-license-issue-draft.md) has been prepared asking the upstream author to add an explicit `LICENSE`. Until that is resolved, please do not redistribute builds of this fork.

Original work © rudrakabir — https://github.com/rudrakabir/voice-memos-exporter

If the original project is useful to you, consider supporting its author:<br>
☕ [Buy Me a Coffee](https://www.buymeacoffee.com/rudrakabir)
