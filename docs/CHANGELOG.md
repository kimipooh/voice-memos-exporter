# Changelog

All notable changes to Voice Memos Exporter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - fork

The upstream `1.0.2` tag is not recorded in the upstream changelog.
Entries below that mention the GUI or app packaging record work completed before the later CLI-only decision; the Removed section records their subsequent removal.

### Fixed

- Excluded recordings in Recently Deleted from default CLI and GUI listing, search, dry-run, and export based on `ZEVICTIONDATE`.
- Preserved GUI selections across search and filtering by replacing stale Treeview item IDs with stable recording keys (upstream Issue #7).
- Sanitized `/`, `\`, `:`, control characters, empty names, and overlong UTF-8 filenames, fixing export failures for titles containing `/` (upstream Issue #2).
- Coerced database and title values safely so numeric-only titles no longer raise `TypeError`.
- Continued processing after an individual recording fails and reported Total / Exported / Skipped / Failed.
- Used the source path loaded with each recording instead of querying again by displayed title and date.
- Ensured generated destinations cannot escape the selected export directory.

### Changed

- The fork now focuses exclusively on the Python command-line interface.
- Set exported-file `mtime` and `atime` from the recording's `ZDATE`; creation time is not explicitly set or preserved (partial support for upstream Issue #1).
- Classified recognized iCloud placeholders as not downloaded and skipped rather than failed.
- Moved GUI copying to a worker thread with progress and cancellation.
- Requested `target_arch='universal2'` in the PyInstaller spec; the Universal 2 build remains unverified (upstream Issue #4).

### Added

- Added inclusive date-range filtering with `--from` and `--to`, including date-only whole-day handling, local-time comparison, and combinations with listing, search, trash inclusion, dry-run, and JSON output.
- Added `Recording.is_trashed`, the `--include-trash` CLI option, list status display, and additive JSON `status` values.
- Added `vmx_core.py` as the shared database and export layer for the CLI and GUI.
- Added `export_voice_memos.py` with listing, JSON output, search, full export, dry-run, database override, timestamp control, and documented exit codes.
- Added recording counts to CLI listings and the GUI window title (upstream Issue #3).
- Added safe unique destination generation and per-recording diagnostic logs.
- Added read-only database access with temporary snapshots when required for WAL handling.
- Added database diagnostics for missing, permission-denied, incompatible-schema, locked, corrupt, and unknown states.
- Added `unittest` regression coverage for database access, filenames, destinations, exports, CLI behavior, and GUI selection.

### Removed

- Removed the Tkinter GUI and its GUI-only tests.
- Removed PyInstaller/macOS app packaging files and related image assets.
- Removed `requirements.txt`, which contained only the packaging-time PyInstaller dependency; the CLI uses only the Python standard library.

### Security

- Opened the Voice Memos database read-only and left the original database and recordings unchanged.
- Added no network communication, telemetry, analytics, or data collection.
- Kept diagnostic logs local to the user-selected output directory; logs contain metadata and paths but no audio.

### Documentation

- Simplified `README.md` and `README-ja.md` into a short entry point (features, requirements, quick start, common examples, main options, notes/limitations, documentation links) and moved detailed CLI reference and internal design notes to new `docs/usage.md` / `docs/usage-ja.md` and `docs/design.md` / `docs/design-ja.md`.
- Removed `docs/audit/` from Git tracking (kept locally, added to `.gitignore`) and removed public links to it from `README.md`, `README-ja.md`, `docs/design.md`, `docs/design-ja.md`, and `docs/CONTRIBUTING.md`; license wording was rephrased to avoid depending on it.
- Standardized `README-ja.md`, `docs/usage-ja.md`, and `docs/design-ja.md` on Japanese prose for headings and explanations, keeping CLI options, code identifiers, and literal CLI output in their original form.
- Added a `NOTICE` file and a short Copyright section in `README.md` / `README-ja.md` recording a copyright notice for fork modifications and newly written code by Kimiya Kitani; this does not add or claim an OSS license.

## [1.0.1] - 2024-12-17

### Fixed
- Search functionality now properly refreshes results
- Fixed issue with exported filenames not matching original recordings
- Improved file naming consistency

## [1.0.0] - 2024-12-16

### Added
- Initial release
- Bulk export capability
- Search functionality
- Progress tracking for exports
- Smart naming for duplicate files
- Full Disk Access handling
- Privacy-focused local operation
