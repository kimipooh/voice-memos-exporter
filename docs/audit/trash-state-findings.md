# Voice Memos Recently Deleted state findings

Investigation date: 2026-08-27

## Safety

The live `CloudRecordings.db` was opened through a SQLite read-only URI. Only
`SELECT` and `PRAGMA` statements were issued. No recording title or recording
path is retained in this audit note.

## Observed schema and values

`ZCLOUDRECORDING` contained 9 rows and 29 columns. Of the deletion/status
candidates, `ZFLAGS` and `ZEVICTIONDATE` existed. No `ZDELETED`,
`ZDELETIONDATE`, `ZMARKEDFORDELETION`, `ZSTATE`, or `ZTRASHED` column existed.

- `ZFLAGS` was `5636` for all 9 rows and did not distinguish the groups.
- `ZEVICTIONDATE` was `NULL` for 5 rows.
- `ZEVICTIONDATE` was a Core Data timestamp for 4 rows.
- All 9 source files were locally present, so local availability did not
  distinguish the groups.

The 5 rows with `ZEVICTIONDATE IS NULL` matched the 5 recordings reported as
visible in the Voice Memos normal list. The 4 rows with
`ZEVICTIONDATE IS NOT NULL` matched, title for title, the 4 recordings reported
as moved to Recently Deleted on the iPhone and absent from the normal list.

## Implemented interpretation

For this observed macOS Voice Memos schema, a non-NULL `ZEVICTIONDATE` is
treated as the Recently Deleted/trash marker. The one-to-one 5/4 match gives
high confidence for this database. This is an empirical interpretation of an
undocumented application database field, not a public Apple API guarantee.

If a compatible database lacks `ZEVICTIONDATE`, recordings are treated as
active because no measured trash marker is available.
