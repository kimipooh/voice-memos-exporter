#!/usr/bin/env python3
"""Read-only diagnostic probe for the Voice Memos database.

Purpose
-------
Confirm the real on-disk schema so the exporter can be built on a *stable*
recording identity instead of the historical upstream GUI's Treeview item IDs.

Safety guarantees
-----------------
* The database is opened with the SQLite URI flag ``mode=ro``. No write,
  no schema change, no WAL/-shm creation by this script.
* Only SELECT / PRAGMA statements are issued.
* No recording titles, no file contents and no absolute personal paths are
  printed. Text values are reported as length + character-class summaries.
* Nothing is sent anywhere; output goes to stdout only.

Usage
-----
    python3 tools/probe_schema.py
"""

import os
import sqlite3
import sys
import unicodedata

DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/group.com.apple.VoiceMemos.shared"
    "/Recordings/CloudRecordings.db"
)
RECORDINGS_DIR = os.path.dirname(DB_PATH)


def hr(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def open_ro(path):
    """Open strictly read-only. Returns (conn, None) or (None, exception)."""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.execute("SELECT 1")
        return conn, None
    except Exception as exc:  # noqa: BLE001 - diagnostic tool
        return None, exc


def classify(text):
    """Describe a string without revealing it."""
    if text is None:
        return "NULL"
    if not isinstance(text, str):
        return f"non-str({type(text).__name__})"
    scripts = set()
    for ch in text:
        if ch.isascii():
            scripts.add("ascii")
        else:
            try:
                scripts.add(unicodedata.name(ch).split()[0].lower())
            except ValueError:
                scripts.add("unnamed")
    flags = []
    if "/" in text:
        flags.append("HAS_SLASH")
    if "\\" in text:
        flags.append("HAS_BACKSLASH")
    if ":" in text:
        flags.append("HAS_COLON")
    if text != text.strip():
        flags.append("LEAD_TRAIL_SPACE")
    if text.strip() == "":
        flags.append("BLANK")
    if text.strip(".") == "":
        flags.append("DOTS_ONLY")
    if text.isdigit():
        flags.append("DIGITS_ONLY")
    if unicodedata.normalize("NFC", text) != text:
        flags.append("NOT_NFC")
    return f"len={len(text)} scripts={sorted(scripts)} {' '.join(flags)}".strip()


def main():
    hr("0. Environment")
    print(f"python           : {sys.version.split()[0]}")
    print(f"sqlite3 lib      : {sqlite3.sqlite_version}")
    print(f"db path exists   : {os.path.exists(DB_PATH)}")
    for suffix in ("-wal", "-shm", "-journal"):
        p = DB_PATH + suffix
        print(f"  {suffix:<9}      : exists={os.path.exists(p)}")

    hr("1. Read-only open")
    conn, exc = open_ro(DB_PATH)
    if conn is None:
        print(f"FAILED: {type(exc).__name__}: {exc}")
        print("\n-> Full Disk Access is probably not granted to this terminal.")
        print("   System Settings > Privacy & Security > Full Disk Access")
        print("   Add the terminal app, then QUIT and REOPEN it.")
        return 1
    print("OK (mode=ro)")
    print("journal_mode  :", conn.execute("PRAGMA journal_mode").fetchone()[0])
    print("user_version  :", conn.execute("PRAGMA user_version").fetchone()[0])

    hr("2. Tables")
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for t in tables:
        print(" ", t)

    if "ZCLOUDRECORDING" not in tables:
        print("\n!! ZCLOUDRECORDING missing -> schema incompatible")
        return 2

    hr("3. ZCLOUDRECORDING columns")
    cols = conn.execute("PRAGMA table_info(ZCLOUDRECORDING)").fetchall()
    for cid, name, ctype, notnull, dflt, pk in cols:
        print(f"  {name:<28} {ctype or '<none>':<10} pk={pk} notnull={notnull}")
    colnames = [c[1] for c in cols]

    hr("4. Stable-identity candidates")
    total = conn.execute("SELECT COUNT(*) FROM ZCLOUDRECORDING").fetchone()[0]
    print(f"row count: {total}")
    for cand in ("Z_PK", "ZUNIQUEID", "ZPATH", "ZCUSTOMLABEL"):
        if cand not in colnames:
            print(f"  {cand:<14} ABSENT")
            continue
        nn, distinct = conn.execute(
            f"SELECT COUNT({cand}), COUNT(DISTINCT {cand}) FROM ZCLOUDRECORDING"
        ).fetchone()
        unique = "UNIQUE" if distinct == total and nn == total else "not unique/nullable"
        print(f"  {cand:<14} non_null={nn:<6} distinct={distinct:<6} {unique}")

    hr("5. Columns hinting at iCloud / eviction state")
    for name in colnames:
        if any(k in name for k in ("EVICT", "CLOUD", "DOWNLOAD", "UPLOAD",
                                   "FLAG", "STATE", "LOCAL", "SYNC", "AVAIL")):
            nn = conn.execute(
                f"SELECT COUNT({name}) FROM ZCLOUDRECORDING").fetchone()[0]
            sample = conn.execute(
                f"SELECT DISTINCT {name} FROM ZCLOUDRECORDING "
                f"WHERE {name} IS NOT NULL LIMIT 6").fetchall()
            print(f"  {name:<28} non_null={nn:<6} distinct_sample={[s[0] for s in sample]}")

    hr("6. ZPATH shape (no titles printed)")
    rows = conn.execute(
        "SELECT ZPATH FROM ZCLOUDRECORDING WHERE ZPATH IS NOT NULL LIMIT 2000"
    ).fetchall()
    absolute = sum(1 for (p,) in rows if os.path.isabs(p))
    with_sep = sum(1 for (p,) in rows if os.sep in p)
    exts = {}
    for (p,) in rows:
        exts[os.path.splitext(p)[1].lower()] = exts.get(os.path.splitext(p)[1].lower(), 0) + 1
    null_path = conn.execute(
        "SELECT COUNT(*) FROM ZCLOUDRECORDING WHERE ZPATH IS NULL OR ZPATH=''").fetchone()[0]
    print(f"sampled          : {len(rows)}")
    print(f"absolute paths   : {absolute}")
    print(f"contain '/'      : {with_sep}")
    print(f"extensions       : {exts}")
    print(f"NULL/empty ZPATH : {null_path}   <- these are hidden by upstream's `if path:`")

    hr("7. Local availability of source files")
    present = missing = placeholder = 0
    for (p,) in rows:
        src = os.path.join(RECORDINGS_DIR, p)
        if os.path.exists(src):
            present += 1
            continue
        holder = os.path.join(os.path.dirname(src),
                              "." + os.path.basename(src) + ".icloud")
        if os.path.exists(holder):
            placeholder += 1
        else:
            missing += 1
    print(f"present on disk         : {present}")
    print(f".icloud placeholder     : {placeholder}")
    print(f"absent, no placeholder  : {missing}")

    hr("8. Title hazards (classified, never printed verbatim)")
    if "ZENCRYPTEDTITLE" in colnames:
        titles = conn.execute(
            "SELECT ZENCRYPTEDTITLE FROM ZCLOUDRECORDING LIMIT 2000").fetchall()
        buckets = {}
        for (t,) in titles:
            for flag in classify(t).split():
                if flag.isupper() and "=" not in flag:
                    buckets[flag] = buckets.get(flag, 0) + 1
        print("null titles      :", sum(1 for (t,) in titles if t is None))
        print("hazard counts    :", buckets or "{} (none)")
        longest = max((len(t) for (t,) in titles if isinstance(t, str)), default=0)
        print("longest title len:", longest)
    else:
        print("ZENCRYPTEDTITLE absent")

    hr("9. Duplicate (date, title) pairs — breaks upstream's re-lookup")
    if {"ZDATE", "ZENCRYPTEDTITLE"} <= set(colnames):
        dup = conn.execute("""
            SELECT COUNT(*) FROM (
              SELECT CAST(ZDATE AS INTEGER) d, ZENCRYPTEDTITLE t, COUNT(*) n
              FROM ZCLOUDRECORDING GROUP BY d, t HAVING n > 1)
        """).fetchone()[0]
        same_sec = conn.execute("""
            SELECT COUNT(*) FROM (
              SELECT CAST(ZDATE AS INTEGER) d, COUNT(*) n
              FROM ZCLOUDRECORDING GROUP BY d HAVING n > 1)
        """).fetchone()[0]
        print(f"duplicate (second, title) groups : {dup}")
        print(f"duplicate second-only groups     : {same_sec}")

    hr("10. NULL numeric fields — upstream crashes the whole list load on these")
    for name in ("ZDATE", "ZDURATION"):
        if name in colnames:
            n = conn.execute(
                f"SELECT COUNT(*) FROM ZCLOUDRECORDING WHERE {name} IS NULL").fetchone()[0]
            print(f"  {name} IS NULL : {n}")

    conn.close()
    print("\nDone. Database was opened read-only and left unmodified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
