#!/usr/bin/env python3
"""Command-line interface for Voice Memos Exporter."""

from __future__ import annotations

import argparse
from datetime import datetime, time
import json
import os
import re
import sys
import unicodedata

import vmx_core


class _ArgumentError(Exception):
    pass


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise _ArgumentError(message)


def _parser():
    parser = _ArgumentParser(
        prog="export_voice_memos.py",
        description="List and export recordings from the macOS Voice Memos database.",
        epilog=(
            "Exit codes: 0 = success; 1 = invalid arguments, database/output error, "
            "no search matches during export, or interruption; 2 = export completed "
            "with skipped or failed recordings."
        ),
    )
    parser.add_argument("--list", action="store_true", help="list recordings without exporting")
    parser.add_argument("--all", action="store_true", help="export all recordings")
    parser.add_argument("--search", metavar="TEXT", help="filter titles (case-insensitive)")
    parser.add_argument(
        "--from",
        dest="from_date",
        metavar="DATE",
        help=(
            "include recordings on or after DATE; accepted formats: YYYY-MM-DD, "
            "YYYY-MM-DD HH:MM, or YYYY-MM-DD HH:MM:SS"
        ),
    )
    parser.add_argument(
        "--to",
        dest="to_date",
        metavar="DATE",
        help=(
            "include recordings on or before DATE; accepted formats: YYYY-MM-DD, "
            "YYYY-MM-DD HH:MM, or YYYY-MM-DD HH:MM:SS; a date without a time "
            "includes the entire day"
        ),
    )
    parser.add_argument("--output", "-o", metavar="DIR", help="export destination directory")
    parser.add_argument("--dry-run", action="store_true", help="show exports without writing files")
    parser.add_argument("--json", action="store_true", help="write --list output as JSON")
    parser.add_argument(
        "--include-trash",
        action="store_true",
        help="include recordings in Recently Deleted",
    )
    parser.add_argument("--db", default=vmx_core.DEFAULT_DB_PATH, metavar="PATH", help="Voice Memos database path")
    parser.add_argument("--no-set-times", action="store_true", help="do not set exported file timestamps")
    parser.add_argument("--version", action="version", version=vmx_core.TOOL_VERSION)
    return parser


def _clean_line(value):
    return "".join(" " if unicodedata.category(char).startswith("C") else char for char in str(value))


def _parse_date_argument(value, option, *, end_of_day=False):
    formats = (
        (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d", True),
        (r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}", "%Y-%m-%d %H:%M", False),
        (r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "%Y-%m-%d %H:%M:%S", False),
    )
    for pattern, date_format, date_only in formats:
        if re.fullmatch(pattern, value):
            try:
                parsed = datetime.strptime(value, date_format)
            except ValueError:
                break
            if date_only and end_of_day:
                return datetime.combine(parsed.date(), time.max)
            return parsed
    raise ValueError(
        f"{option} must use YYYY-MM-DD, YYYY-MM-DD HH:MM, or YYYY-MM-DD HH:MM:SS"
    )


def _local_value(recordings_dir, recording):
    state, _ = vmx_core.resolve_source(recordings_dir, recording.rel_path)
    return {
        vmx_core.SourceState.AVAILABLE: "yes",
        vmx_core.SourceState.NOT_DOWNLOADED: "icloud",
        vmx_core.SourceState.MISSING: "missing",
    }[state]


def _duration(value):
    return vmx_core.format_duration(value)


def _list_recordings(
    all_recordings,
    selected,
    recordings_dir,
    as_json,
    filtered=False,
    show_status=False,
):
    if as_json:
        payload = [
            {
                "key": recording.key,
                "date": recording.date.isoformat() if recording.date else None,
                "duration": recording.duration,
                "local": _local_value(recordings_dir, recording),
                "status": "trash" if recording.is_trashed else "active",
                "title": _clean_line(recording.title),
            }
            for recording in selected
        ]
        print(json.dumps(payload, ensure_ascii=False))
        return

    if filtered:
        print(f"Total recordings: {len(all_recordings)} (matched: {len(selected)})")
    else:
        print(f"Total recordings: {len(all_recordings)}")
    if show_status:
        print(f"{'KEY':<18} {'DATE':<16} {'DURATION':>8} {'LOCAL':<7} {'STATUS':<7} TITLE")
    else:
        print(f"{'KEY':<18} {'DATE':<16} {'DURATION':>8} {'LOCAL':<7} TITLE")
    for recording in selected:
        date = recording.date.strftime("%Y-%m-%d %H:%M") if recording.date else "-"
        status = "trash" if recording.is_trashed else "active"
        status_column = f"{status:<7} " if show_status else ""
        print(
            f"{_clean_line(recording.key):<18} {date:<16} "
            f"{_duration(recording.duration):>8} {_local_value(recordings_dir, recording):<7} "
            f"{status_column}{_clean_line(recording.title)}"
        )


def _diagnosis_message(diagnosis):
    if diagnosis.status is vmx_core.DbStatus.PERMISSION_DENIED:
        return (
            "Permission denied reading the Voice Memos database. Full Disk Access is required; "
            "grant it to Terminal, iTerm, or the process that actually starts Python."
        )
    return f"Cannot open Voice Memos database: {diagnosis.detail}"


def _print_export(summary, dry_run):
    prefix = "[dry-run] " if dry_run else ""
    for index, record in enumerate(summary.records, 1):
        if record.outcome is vmx_core.Outcome.EXPORTED:
            status = "would export" if dry_run else "exported"
            detail = os.path.basename(record.dest_path) if record.dest_path else _clean_line(record.title)
        elif record.outcome is vmx_core.Outcome.SKIPPED_NOT_DOWNLOADED:
            status = "skipped"
            detail = f"(icloud) {_clean_line(record.title)}"
        elif record.outcome is vmx_core.Outcome.SKIPPED_CANCELLED:
            status = "skipped"
            detail = f"(cancelled) {_clean_line(record.title)}"
        else:
            status = "failed"
            error = f"{record.error_type}: {record.error_message}" if record.error_type else "Unknown error"
            detail = f"{_clean_line(record.title)} — {_clean_line(error)}"
        print(f"{prefix}[{index}/{summary.total}] {status:<12} {detail}")


def main(argv=None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        if not (args.list or args.all or args.search is not None):
            parser.error("one of --list, --all, or --search is required")
        exporting = not args.list and (args.all or args.search is not None)
        if exporting and not args.output:
            parser.error("--output is required when exporting")

        try:
            from_datetime = (
                _parse_date_argument(args.from_date, "--from")
                if args.from_date is not None
                else None
            )
            to_datetime = (
                _parse_date_argument(args.to_date, "--to", end_of_day=True)
                if args.to_date is not None
                else None
            )
        except ValueError as exc:
            parser.error(str(exc))
        if (
            from_datetime is not None
            and to_datetime is not None
            and from_datetime > to_datetime
        ):
            parser.error("--from must be earlier than or equal to --to")

        db_path = os.path.expanduser(args.db)
        diagnosis = vmx_core.diagnose_database(db_path)
        if diagnosis.status is not vmx_core.DbStatus.OK:
            print(_diagnosis_message(diagnosis), file=sys.stderr)
            return 1

        try:
            with vmx_core.open_database(db_path) as conn:
                recordings, warnings = vmx_core.load_recordings(
                    conn, include_trashed=args.include_trash
                )
        except Exception as exc:
            print(f"Cannot load Voice Memos database: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        for warning in warnings:
            print(f"Warning: {warning}", file=sys.stderr)

        date_filtered = vmx_core.filter_recordings(
            recordings,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
        )
        selected = vmx_core.filter_recordings(
            date_filtered,
            search=args.search,
        )
        recordings_dir = os.path.dirname(os.path.abspath(db_path))
        if args.list:
            _list_recordings(
                date_filtered,
                selected,
                recordings_dir,
                args.json,
                filtered=args.search is not None,
                show_status=args.include_trash,
            )
            return 0
        if args.search is not None and not selected:
            print("No recordings matched the search text.", file=sys.stderr)
            return 1

        output = os.path.abspath(os.path.expanduser(args.output))
        if not args.dry_run:
            try:
                os.makedirs(output, exist_ok=True)
                if not os.path.isdir(output):
                    raise NotADirectoryError("output path is not a directory")
            except OSError as exc:
                print(f"Cannot create output directory: {type(exc).__name__}: {exc}", file=sys.stderr)
                return 1

        summary = vmx_core.export_recordings(
            selected,
            output,
            recordings_dir=recordings_dir,
            set_times=not args.no_set_times,
            dry_run=args.dry_run,
        )
        _print_export(summary, args.dry_run)
        if not args.dry_run:
            summary.log_path = vmx_core.write_log(output, summary, db_diagnosis=diagnosis)
        print(f"Total:    {summary.total}")
        print(f"Exported: {summary.exported}")
        print(f"Skipped:  {summary.skipped}")
        print(f"Failed:   {summary.failed}")
        if summary.log_path:
            print(f"Log:      {summary.log_path}")
        return 2 if summary.failed or summary.skipped else 0
    except _ArgumentError:
        return 1
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
