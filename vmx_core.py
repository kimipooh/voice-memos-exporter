"""GUI-independent database and export logic for Voice Memos Exporter."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import errno
import json
import math
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import sys
import tempfile
import unicodedata
from urllib.parse import quote


DEFAULT_DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings/CloudRecordings.db"
)
APPLE_EPOCH_OFFSET = 978307200
TOOL_VERSION = "1.0.3"


class DbStatus(Enum):
    OK = "ok"
    MISSING = "missing"
    PERMISSION_DENIED = "permission_denied"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"
    LOCKED = "locked"
    CORRUPT = "corrupt"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DbDiagnosis:
    status: DbStatus
    detail: str
    exception_type: str | None
    exception_message: str | None
    db_path: str
    recordings_dir_readable: bool


@dataclass(frozen=True)
class Recording:
    key: str
    pk: int | None
    unique_id: str | None
    rel_path: str
    title: str
    date: datetime | None
    duration: float | None
    date_epoch: float | None = None
    is_trashed: bool = False


class SourceState(Enum):
    AVAILABLE = "available"
    NOT_DOWNLOADED = "not_downloaded"
    MISSING = "missing"


class Outcome(Enum):
    EXPORTED = "exported"
    SKIPPED_NOT_DOWNLOADED = "skipped_not_downloaded"
    SKIPPED_CANCELLED = "skipped_cancelled"
    FAILED = "failed"


@dataclass
class ExportRecord:
    recording_key: str
    title: str
    source_path: str | None
    dest_path: str | None
    outcome: Outcome
    error_type: str | None
    error_message: str | None


@dataclass
class ExportSummary:
    total: int
    exported: int
    skipped: int
    failed: int
    records: list[ExportRecord]
    log_path: str | None


def connect_readonly(db_path: str) -> sqlite3.Connection:
    """Open an existing SQLite database without permitting writes."""
    quoted = quote(os.path.abspath(db_path), safe="/")
    conn = sqlite3.connect(f"file:{quoted}?mode=ro", uri=True)
    try:
        conn.execute("SELECT 1").fetchone()
    except Exception:
        conn.close()
        raise
    return conn


@contextmanager
def open_database(db_path):
    """Yield a read-only connection without creating files beside the source DB."""
    connection = None
    snapshot_dir = None
    if os.path.exists(f"{db_path}-shm"):
        try:
            candidate = connect_readonly(db_path)
            try:
                candidate.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
            except sqlite3.OperationalError:
                candidate.close()
                raise
            connection = candidate
        except sqlite3.OperationalError:
            connection = None

    try:
        if connection is None:
            snapshot_dir = tempfile.mkdtemp(prefix="voice-memos-exporter-")
            snapshot_db = os.path.join(snapshot_dir, os.path.basename(db_path))
            for suffix in ("", "-wal", "-shm"):
                source = f"{db_path}{suffix}"
                if os.path.exists(source):
                    shutil.copy2(source, f"{snapshot_db}{suffix}")
            connection = connect_readonly(snapshot_db)
        yield connection
    finally:
        if connection is not None:
            connection.close()
        if snapshot_dir is not None:
            shutil.rmtree(snapshot_dir, ignore_errors=True)


def _recordings_dir_readable(db_path: str) -> bool:
    directory = os.path.dirname(os.path.abspath(db_path))
    try:
        with os.scandir(directory) as entries:
            next(entries, None)
        return True
    except OSError:
        return False


def _diagnosis(status, detail, db_path, exc=None):
    return DbDiagnosis(
        status=status,
        detail=detail,
        exception_type=type(exc).__name__ if exc else None,
        exception_message=str(exc) if exc else None,
        db_path=db_path,
        recordings_dir_readable=_recordings_dir_readable(db_path),
    )


def _classify_sqlite_error(exc):
    message = str(exc).lower()
    if "authorization denied" in message or "unable to open database file" in message:
        return DbStatus.PERMISSION_DENIED
    if "database is locked" in message or "database table is locked" in message:
        return DbStatus.LOCKED
    if any(text in message for text in ("file is not a database", "malformed", "encrypted")):
        return DbStatus.CORRUPT
    return DbStatus.UNKNOWN


def diagnose_database(db_path: str) -> DbDiagnosis:
    if not os.path.exists(db_path):
        return _diagnosis(DbStatus.MISSING, "Voice Memos database not found", db_path)
    try:
        with open(db_path, "rb") as db_file:
            db_file.read(16)
    except PermissionError as exc:
        return _diagnosis(DbStatus.PERMISSION_DENIED, "Permission denied reading database", db_path, exc)
    except OSError as exc:
        if exc.errno in (errno.EPERM, errno.EACCES):
            return _diagnosis(DbStatus.PERMISSION_DENIED, "Permission denied reading database", db_path, exc)
        return _diagnosis(DbStatus.UNKNOWN, "Unable to read database header", db_path, exc)

    try:
        with open_database(db_path) as conn:
            table = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ZCLOUDRECORDING'"
            ).fetchone()
            if not table:
                return _diagnosis(
                    DbStatus.SCHEMA_INCOMPATIBLE, "ZCLOUDRECORDING table is missing", db_path
                )
            columns = {row[1] for row in conn.execute("PRAGMA table_info(ZCLOUDRECORDING)")}
            if "ZPATH" not in columns:
                return _diagnosis(
                    DbStatus.SCHEMA_INCOMPATIBLE,
                    "ZCLOUDRECORDING.ZPATH column is missing",
                    db_path,
                )
    except sqlite3.Error as exc:
        status = _classify_sqlite_error(exc)
        return _diagnosis(status, f"Database error: {exc}", db_path, exc)
    except OSError as exc:
        if exc.errno in (errno.EPERM, errno.EACCES):
            return _diagnosis(
                DbStatus.PERMISSION_DENIED,
                "Permission denied while creating a database snapshot",
                db_path,
                exc,
            )
        return _diagnosis(DbStatus.UNKNOWN, "Unable to create a database snapshot", db_path, exc)
    return _diagnosis(DbStatus.OK, "Database is readable and supported", db_path)


def _optional_number(value, converter):
    if value is None:
        return None
    try:
        result = converter(value)
        if isinstance(result, float) and not math.isfinite(result):
            return None
        return result
    except (TypeError, ValueError, OverflowError):
        return None


def _coerce_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "replace")
    return str(value)


def load_recordings(
    conn: sqlite3.Connection, *, include_trashed: bool = False
) -> tuple[list[Recording], list[str]]:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(ZCLOUDRECORDING)")}
    if "ZPATH" not in columns:
        raise sqlite3.OperationalError("ZCLOUDRECORDING.ZPATH column is missing")
    optional = [
        name
        for name in (
            "Z_PK",
            "ZUNIQUEID",
            "ZENCRYPTEDTITLE",
            "ZCUSTOMLABEL",
            "ZDATE",
            "ZDURATION",
            "ZEVICTIONDATE",
        )
        if name in columns
    ]
    selected = ["ZPATH", *optional]
    order = " ORDER BY ZDATE DESC" if "ZDATE" in columns else (
        " ORDER BY Z_PK DESC" if "Z_PK" in columns else ""
    )
    rows = conn.execute(f"SELECT {', '.join(selected)} FROM ZCLOUDRECORDING{order}").fetchall()

    recordings = []
    warnings = []
    missing_paths = 0
    used_keys = set()
    for raw_row in rows:
        row = dict(zip(selected, raw_row))
        is_trashed = row.get("ZEVICTIONDATE") is not None
        if is_trashed and not include_trashed:
            continue
        rel_path = _coerce_text(row.get("ZPATH"))
        if rel_path in (None, ""):
            missing_paths += 1
            continue
        pk = _optional_number(row.get("Z_PK"), int)
        unique_id = _coerce_text(row.get("ZUNIQUEID"))
        if unique_id == "":
            unique_id = None
        title_value = next(
            (
                text
                for text in (
                    _coerce_text(row.get("ZENCRYPTEDTITLE")),
                    _coerce_text(row.get("ZCUSTOMLABEL")),
                )
                if text not in (None, "")
            ),
            None,
        )
        fallback_title = os.path.splitext(os.path.basename(rel_path))[0]
        title = title_value if title_value is not None else fallback_title
        date_seconds = _optional_number(row.get("ZDATE"), float)
        date_epoch = date_seconds + APPLE_EPOCH_OFFSET if date_seconds is not None else None
        try:
            date = datetime.fromtimestamp(date_epoch) if date_epoch is not None else None
        except (OSError, OverflowError, ValueError):
            date = None
            date_epoch = None
        duration = _optional_number(row.get("ZDURATION"), float)
        base_key = f"pk:{pk}" if pk is not None else (
            f"uid:{unique_id}" if unique_id is not None else f"path:{rel_path}"
        )
        key = base_key
        suffix = 2
        while key in used_keys:
            key = f"{base_key}#{suffix}"
            suffix += 1
        if key != base_key:
            warnings.append(f"Duplicate recording key {base_key!r}; assigned {key!r}")
        used_keys.add(key)
        recordings.append(
            Recording(
                key,
                pk,
                unique_id,
                rel_path,
                title,
                date,
                duration,
                date_epoch,
                is_trashed,
            )
        )
    if missing_paths:
        warnings.append(f"Excluded {missing_paths} recording(s) with an empty ZPATH")
    return recordings, warnings


def _clean_stem(value):
    value = unicodedata.normalize("NFC", str(value))
    value = "".join(char for char in value if not (ord(char) < 32 or ord(char) == 127))
    return value.replace("/", "-").replace("\\", "-").replace(":", "-").strip(" .")


def safe_filename(title, ext, *, fallback, max_bytes=200) -> str:
    stem = _clean_stem(title)
    if stem in ("", ".", ".."):
        stem = _clean_stem(fallback)
    stem = stem.lstrip(".").strip(" .")
    if not stem:
        stem = "recording"
    encoded = stem.encode("utf-8")
    if len(encoded) > max_bytes:
        stem = encoded[:max_bytes].decode("utf-8", "ignore").rstrip(" .")
    if not stem:
        stem = "recording"
    return f"{stem}{str(ext)}"


def unique_destination(export_dir: str, filename: str, taken: set[str]) -> str:
    export_root = os.path.realpath(export_dir)
    base, ext = os.path.splitext(filename)
    counter = 0
    while True:
        candidate_name = filename if counter == 0 else f"{base}_{counter}{ext}"
        dest = os.path.join(export_dir, candidate_name)
        real_dest = os.path.realpath(dest)
        if not real_dest.startswith(export_root + os.sep):
            raise ValueError("Destination path escapes the export directory")
        if not os.path.exists(dest) and real_dest not in taken:
            taken.add(real_dest)
            return dest
        counter += 1


def resolve_source(recordings_dir: str, rel_path: str) -> tuple[SourceState, str]:
    src = os.path.join(recordings_dir, rel_path)
    if os.path.exists(src):
        return SourceState.AVAILABLE, src
    placeholder = os.path.join(os.path.dirname(src), f".{os.path.basename(src)}.icloud")
    if os.path.exists(placeholder):
        return SourceState.NOT_DOWNLOADED, src
    return SourceState.MISSING, src


def _result(rec, source_path, dest_path, outcome, error_type=None, error_message=None):
    return ExportRecord(
        rec.key, rec.title, source_path, dest_path, outcome, error_type, error_message
    )


def export_recordings(
    recordings,
    export_dir,
    *,
    recordings_dir,
    progress=None,
    cancel=None,
    set_times=True,
    dry_run=False,
) -> ExportSummary:
    items = list(recordings)
    total = len(items)
    records = []
    taken = set()
    for index, rec in enumerate(items):
        if cancel and cancel():
            for remaining_index, remaining in enumerate(items[index:], start=index):
                records.append(
                    _result(
                        remaining,
                        None,
                        None,
                        Outcome.SKIPPED_CANCELLED,
                        "Cancelled",
                        "Export cancelled by user",
                    )
                )
                if progress:
                    progress(remaining_index + 1, total, remaining.title)
            break
        source_path = None
        dest_path = None
        try:
            state, source_path = resolve_source(recordings_dir, rec.rel_path)
            if state is SourceState.NOT_DOWNLOADED:
                records.append(
                    _result(
                        rec,
                        source_path,
                        None,
                        Outcome.SKIPPED_NOT_DOWNLOADED,
                        "NotDownloaded",
                        "File not available locally (iCloud)",
                    )
                )
                continue
            if state is SourceState.MISSING:
                raise FileNotFoundError("Source file missing")
            fallback = os.path.splitext(os.path.basename(rec.rel_path))[0]
            if not _clean_stem(fallback):
                fallback = f"recording_{rec.key.replace(':', '_')}"
            filename = safe_filename(rec.title, os.path.splitext(source_path)[1], fallback=fallback)
            if dry_run:
                dest_path = unique_destination(export_dir, filename, taken)
                records.append(_result(rec, source_path, dest_path, Outcome.EXPORTED))
                continue
            for _ in range(1000):
                dest_path = unique_destination(export_dir, filename, taken)
                try:
                    fd = os.open(dest_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
                except FileExistsError:
                    continue
                try:
                    with open(source_path, "rb") as source, os.fdopen(fd, "wb") as destination:
                        shutil.copyfileobj(source, destination)
                    if set_times and rec.date_epoch is not None:
                        os.utime(dest_path, (rec.date_epoch, rec.date_epoch))
                except Exception:
                    Path(dest_path).unlink(missing_ok=True)
                    raise
                records.append(_result(rec, source_path, dest_path, Outcome.EXPORTED))
                break
            else:
                raise FileExistsError("Unable to reserve a unique destination after 1000 attempts")
        except Exception as exc:
            records.append(
                _result(rec, source_path, dest_path, Outcome.FAILED, type(exc).__name__, str(exc))
            )
        finally:
            if progress:
                progress(index + 1, total, rec.title)
    exported = sum(record.outcome is Outcome.EXPORTED for record in records)
    skipped = sum(
        record.outcome in (Outcome.SKIPPED_NOT_DOWNLOADED, Outcome.SKIPPED_CANCELLED)
        for record in records
    )
    failed = sum(record.outcome is Outcome.FAILED for record in records)
    return ExportSummary(total, exported, skipped, failed, records, None)


def write_log(export_dir, summary, *, db_diagnosis=None) -> str | None:
    if summary.skipped + summary.failed == 0:
        return None
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        path = unique_destination(
            export_dir, f"voice-memos-exporter-{timestamp}.log", set()
        )
        with open(path, "x", encoding="utf-8") as log_file:
            header = {
                "tool_version": TOOL_VERSION,
                "macOS": platform.mac_ver()[0],
                "python": sys.version.split()[0],
                "total": summary.total,
                "exported": summary.exported,
                "skipped": summary.skipped,
                "failed": summary.failed,
                "database": (
                    {
                        "status": db_diagnosis.status.value,
                        "detail": db_diagnosis.detail,
                        "exception_type": db_diagnosis.exception_type,
                        "exception_message": db_diagnosis.exception_message,
                    }
                    if db_diagnosis
                    else None
                ),
            }
            log_file.write(json.dumps(header, ensure_ascii=False) + "\n")
            for record in summary.records:
                payload = {
                    "recording_key": record.recording_key,
                    "title": record.title,
                    "source_path": record.source_path,
                    "dest_path": record.dest_path,
                    "outcome": record.outcome.value,
                    "error_type": record.error_type,
                    "error_message": record.error_message,
                }
                log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return path
    except (OSError, UnicodeError):
        return None
