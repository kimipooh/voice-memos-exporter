# GUI local notes

The Tkinter GUI, `voice_memos_exporter.py`, exists only on the local branch
`gui/local-app`. It is not published, released, or distributed.

Its UI structure is derived from `rudrakabir/voice-memos-exporter`. The database
access and export logic were replaced by this fork's `vmx_core` module.

The upstream license status is unresolved. Do not add a `LICENSE` file or SPDX
identifier while that remains unresolved.

`vmx_core.py` is the single export engine. The GUI and the CLI,
`export_voice_memos.py`, are two front ends over the same core API. The GUI does
not parse CLI stdout and does not shell out to the CLI.

Run the GUI with:

```bash
python3 voice_memos_exporter.py
```

Grant Full Disk Access to the terminal application that runs Python, not to a
`.app` bundle.

For local `.app` packaging, see [gui-local-packaging.md](gui-local-packaging.md).

## Attribution

The About dialog shows the upstream project and the fork modifications
separately. The packaged app carries the same attribution string in the
`Info.plist` `NSHumanReadableCopyright` field.

## Manual test checklist

The automated tests cover the view model and the export call, but never touch a
real Voice Memos database. Run this checklist by hand against a real library
before treating a GUI change as done.

Full Disk Access

- [ ] Revoke Full Disk Access from the terminal, then start the GUI. The Full
      Disk Access dialog appears, names the terminal application (not a `.app`
      bundle), and states that the tool only reads the database.
- [ ] "Open Security Settings" opens Privacy & Security.
- [ ] With access denied, the status line reads that export is disabled and the
      Export Selected button is greyed out.
- [ ] Grant access, restart the terminal, start the GUI again: recordings load
      and the status line reports the count.

List and columns

- [ ] Title, Date, Duration, Local and Status all render.
- [ ] A recording longer than one hour shows as `H:MM:SS`.
- [ ] A recording with no duration shows `-`.
- [ ] A recording that is not downloaded from iCloud shows Local = `iCloud`.
- [ ] Counts in the window title match the list.

Search, Reload, Recently Deleted

- [ ] Typing in Search narrows the list by title, case-insensitively.
- [ ] Japanese titles match regardless of composed/decomposed input.
- [ ] Searching by a date or duration string does NOT match — search is
      title-only, matching the CLI.
- [ ] "Include Recently Deleted" reloads and adds rows with Status =
      `Recently Deleted`.
- [ ] Reload keeps the search text and keeps the current selection for
      recordings that still exist.

Selection

- [ ] Clicking the Select column toggles a single row.
- [ ] Select All / Deselect All affect only the currently visible rows.
- [ ] Selection survives typing and clearing a search term.

Export

- [ ] Export Selected with nothing selected warns and does nothing.
- [ ] Dry run reports counts, writes no audio files, and writes no log file.
- [ ] A real export copies the files, writes the log, and reports
      Total/Exported/Skipped/Failed.
- [ ] Cancel during a long export stops it and the summary counts the remainder
      as skipped.
- [ ] Exporting a title containing `/` and a numeric-only title both succeed.
- [ ] One unavailable recording does not stop the rest of the export.
- [ ] The Voice Memos database and the original recordings are unchanged
      afterwards.
