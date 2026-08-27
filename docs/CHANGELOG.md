# Changelog

All notable changes to Voice Memos Exporter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - fork

The upstream `1.0.2` tag is not recorded in the upstream changelog.

### Fixed

- Excluded recordings in Recently Deleted from default CLI and GUI listing, search, dry-run, and export based on `ZEVICTIONDATE`.
- Preserved GUI selections across search and filtering by replacing stale Treeview item IDs with stable recording keys (upstream Issue #7).
- Sanitized `/`, `\`, `:`, control characters, empty names, and overlong UTF-8 filenames, fixing export failures for titles containing `/` (upstream Issue #2).
- Coerced database and title values safely so numeric-only titles no longer raise `TypeError`.
- Continued processing after an individual recording fails and reported Total / Exported / Skipped / Failed.
- Used the source path loaded with each recording instead of querying again by displayed title and date.
- Ensured generated destinations cannot escape the selected export directory.

### Changed

- Set exported-file `mtime` and `atime` from the recording's `ZDATE`; creation time is not explicitly set or preserved (partial support for upstream Issue #1).
- Classified recognized iCloud placeholders as not downloaded and skipped rather than failed.
- Moved GUI copying to a worker thread with progress and cancellation.
- Requested `target_arch='universal2'` in the PyInstaller spec; the Universal 2 build remains unverified (upstream Issue #4).

### Added

- Added `Recording.is_trashed`, the `--include-trash` CLI option, list status display, and additive JSON `status` values.
- Added `vmx_core.py` as the shared database and export layer for the CLI and GUI.
- Added `export_voice_memos.py` with listing, JSON output, search, full export, dry-run, database override, timestamp control, and documented exit codes.
- Added recording counts to CLI listings and the GUI window title (upstream Issue #3).
- Added safe unique destination generation and per-recording diagnostic logs.
- Added read-only database access with temporary snapshots when required for WAL handling.
- Added database diagnostics for missing, permission-denied, incompatible-schema, locked, corrupt, and unknown states.
- Added `unittest` regression coverage for database access, filenames, destinations, exports, CLI behavior, and GUI selection.

### Security

- Opened the Voice Memos database read-only and left the original database and recordings unchanged.
- Added no network communication, telemetry, analytics, or data collection.
- Kept diagnostic logs local to the user-selected output directory; logs contain metadata and paths but no audio.

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
