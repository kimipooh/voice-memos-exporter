# Troubleshooting

[日本語版: troubleshooting-ja.md](troubleshooting-ja.md)

Symptoms and fixes for Voice Memos Exporter. For the CLI reference see
[usage.md](usage.md); for building the app see [gui-packaging.md](gui-packaging.md).

## First launch is blocked

**Symptom:** Double-clicking the app shows a warning offering only "Move to Trash" / "Done", and the app does not start.

The app is not signed with an Apple Developer ID certificate and is not notarized, so Gatekeeper blocks the first launch. It is ad-hoc signed only; this is not a malfunction.

On macOS 15 Sequoia and later, Control-click → Open no longer overrides Gatekeeper. Apple announced in [Updates to runtime protection in macOS Sequoia](https://developer.apple.com/news/?id=saqachfa):

> In macOS Sequoia, users will no longer be able to Control-click to override
> Gatekeeper when opening software that isn't signed correctly or notarized.
> They'll need to visit System Settings > Privacy & Security to review security
> information for software before allowing it to run.

Follow Apple's documented steps in this order:

1. On your Mac, choose Apple menu > System Settings, then click **Privacy &
   Security** in the sidebar. (You may need to scroll down.)
2. Go to **Security**, then click **Open**.
3. Click **Open Anyway**.
   - *This button is available for about an hour after you try to open the app.*
4. Enter your login password, then click **OK**.

The app is saved as an exception to your security settings and opens normally by double-clicking in the future. See Apple's [Open a Mac app from an unknown developer](https://support.apple.com/guide/mac-help/mh40616/mac).

## Full Disk Access is required

**Symptom:** The app launches but cannot read the Voice Memos database or recordings.

Gatekeeper decides whether the app is **allowed to launch**. Full Disk Access decides whether the app is **allowed to read** the Voice Memos database and recordings. Both settings are under System Settings → Privacy & Security, so they are easy to confuse, but they are separate and both are required.

1. Choose Apple menu → System Settings → Privacy & Security → Full Disk Access.
2. Add `Voice Memos Exporter.app` and turn access on.
3. Quit the app completely, then reopen it.

For the CLI or GUI run from source, grant Full Disk Access to the **terminal application** that starts Python—Terminal, iTerm, or an IDE's integrated terminal—not to a `.app`, then restart that terminal. When access is missing, the CLI prints guidance and exits with status 1.

Rebuilding the app can change its code-signing identity, so macOS may require Full Disk Access approval again.

## Voice Memos database not found

This message does not necessarily mean the app is broken. It commonly appears when the Voice Memos database has not been created yet, for example when Voice Memos has never been used on this Mac.

- Open Apple's Voice Memos app once.
- Confirm at least one recording exists on this Mac.
- If your recordings are on an iPhone, confirm they have synced to this Mac via iCloud.
- Quit Voice Memos, then start Voice Memos Exporter again.
- If you keep the database somewhere non-default, the CLI accepts `--db PATH`.

## Voice Memos database is locked or cannot be opened

Quit Apple's Voice Memos app and retry. This is different from missing Full Disk Access: a locked database was reachable but busy, while a permission failure reports a permission error. The tool distinguishes missing, permission-denied, incompatible-schema, locked, and corrupt states.

The tool opens the database read-only and may use a temporary read snapshot for WAL handling; it never writes to the original.

## A recording is in iCloud only

A recording can be listed while its audio is not on this Mac. The `Local` column shows `iCloud` in that case. Such recordings are reported as skipped, not failed, and are never downloaded by this tool.

Open Voice Memos and play or download the recording so macOS fetches it locally, then run the export again.

## Some recordings were skipped or failed

Check the `Local` column (`Yes` / `iCloud` / `Missing`), the `Status` column, and whether the output folder is writable.

When at least one recording is skipped or failed, a JSON Lines diagnostic log is written to the output directory and its path is printed. It records the recording identifier, title, source and destination paths, outcome, and exception type/message. It contains no audio and is never transmitted. One failure never stops the rest of the export.

## Recently Deleted recordings

Recently Deleted recordings are excluded by default. Enable **Include Recently Deleted** in the GUI, or use `--include-trash` in the CLI. These rows show `Recently Deleted` in the `Status` column.

Availability depends on Apple's retention of the Recently Deleted folder. Once Voice Memos purges a recording, this tool cannot recover it.

## Apple documentation

- [Open a Mac app from an unknown developer](https://support.apple.com/guide/mac-help/mh40616/mac)
- [Updates to runtime protection in macOS Sequoia](https://developer.apple.com/news/?id=saqachfa)
