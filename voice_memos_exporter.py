"""Voice Memos Exporter — macOS Tkinter GUI front end.

Provenance
----------
Derived from the upstream project ``rudrakabir/voice-memos-exporter``.
Only the upstream UI structure and interaction model are reused here.
All database access and export logic were replaced by this fork's
``vmx_core`` module; no upstream DB or export code remains in this file.

Original work (c) 2026 rudrakabir; fork modifications (c) 2026 Kimiya Kitani.
Licensed under the MIT License. See the LICENSE file at the repository root.
"""

import json
import os
import queue
import subprocess
import sys
import threading

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ModuleNotFoundError as exc:
    if exc.name not in {"tkinter", "_tkinter"}:
        raise
    tk = None
    filedialog = messagebox = ttk = None
    _TK_IMPORT_ERROR = exc
else:
    _TK_IMPORT_ERROR = None

import vmx_core
from vmx_core import (
    DEFAULT_DB_PATH,
    DbStatus,
    SourceState,
    diagnose_database,
    export_recordings,
    filter_recordings as core_filter_recordings,
    format_duration,
    load_recordings,
    open_database,
    resolve_source,
    write_log,
)

APP_NAME = "Voice Memos Exporter"
APP_VERSION = vmx_core.TOOL_VERSION
UPSTREAM_PROJECT = "rudrakabir/voice-memos-exporter"
APP_COPYRIGHT = "Original work © rudrakabir; fork modifications © 2026 Kimiya Kitani"
COLUMNS = ("title", "date", "duration", "local", "status", "checked")
CHECK_COLUMN = f"#{COLUMNS.index('checked') + 1}"
LOCAL_LABELS = {
    SourceState.AVAILABLE: "Yes",
    SourceState.NOT_DOWNLOADED: "iCloud",
    SourceState.MISSING: "Missing",
}


def _is_packaged_app():
    """True when running from the PyInstaller-built .app bundle."""
    return bool(getattr(sys, "frozen", False))


def full_disk_access_steps(packaged):
    if packaged:
        return [
            '1. Click "Open Security Settings" below.',
            "2. Go to Privacy & Security > Full Disk Access.",
            "3. Click + and add Voice Memos Exporter.app.",
            "4. Make sure its checkbox is turned on.",
            "5. Quit and reopen Voice Memos Exporter.app.",
        ]
    return [
        '1. Click "Open Security Settings" below.',
        "2. Go to Privacy & Security > Full Disk Access.",
        "3. Click + and add the terminal application you used to start this tool",
        "   (for example Terminal.app or iTerm.app).",
        "4. Make sure its checkbox is turned on.",
        "5. Quit and reopen that terminal application.",
        "6. Run this tool again: python3 voice_memos_exporter.py",
    ]


def _emit_selftest():
    payload = {
        "frozen": bool(getattr(sys, "frozen", False)),
        "executable": sys.executable,
        "prefix": sys.prefix,
        "meipass": getattr(sys, "_MEIPASS", None),
        "tcl_version": str(tk.TclVersion) if tk is not None else None,
        "tk_version": str(tk.TkVersion) if tk is not None else None,
        "vmx_core_file": getattr(vmx_core, "__file__", None),
        "vmx_core_ok": hasattr(vmx_core, "export_recordings"),
    }
    os.write(1, (json.dumps(payload) + "\n").encode("utf-8"))
    return 0


def local_label(state):
    return LOCAL_LABELS.get(state, "?")


def about_text():
    """Attribution text for the About dialog."""
    return "\n".join(
        [
            APP_NAME,
            f"Version {APP_VERSION}",
            "",
            "Original project:",
            UPSTREAM_PROJECT,
            "Original work © rudrakabir",
            "",
            "Fork modifications:",
            "© 2026 Kimiya Kitani",
            "",
            "Licensed under the MIT License.",
        ]
    )


def status_label(recording):
    return "Recently Deleted" if recording.is_trashed else "Active"


class VoiceMemosExporter:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Memos Exporter")
        self.menubar = None
        self.app_menu = None
        self.create_menubar()
        self.root.geometry("1000x600")
        self.root.minsize(800, 400)
        self.db_path = DEFAULT_DB_PATH
        self.recordings_path = os.path.dirname(self.db_path)
        self.recordings = {}
        self.source_states = {}
        self.selected_keys = set()
        self.row_keys = {}
        self.visible_keys = []
        self.db_diagnosis = None
        self._export_running = False
        self.search_var = tk.StringVar()
        self.include_deleted_var = tk.BooleanVar(value=False)
        self.dry_run_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="")
        self.create_widgets()
        self.search_var.trace_add("write", self.filter_recordings)
        self.load_recordings()

    def create_menubar(self):
        """Register an explicit macOS application menu with an About entry.

        Tk only consults the ``tkAboutDialog`` hook from the About item of its
        own hidden default application menu, so that hook alone is not a
        reliable way to reach this fork's attribution text. A menubar whose
        first cascade is the special ``.apple`` menu replaces that hidden menu:
        Tk keeps its standard Preferences / Services / Hide / Quit items but not
        its own About item, so the About entry added here is the only one.

        The ``tkAboutDialog`` hook stays registered as a secondary path (it adds
        no menu entry of its own), so any About action that Tk still routes
        through the standard about panel shows the same dialog.
        """
        try:
            aqua = self.root.tk.call("tk", "windowingsystem") == "aqua"
        except tk.TclError:
            aqua = False
        if aqua:
            self.menubar = tk.Menu(self.root)
            self.app_menu = tk.Menu(self.menubar, name="apple")
            self.menubar.add_cascade(menu=self.app_menu)
            self.app_menu.add_command(
                label=f"About {APP_NAME}", command=self.show_about_dialog
            )
            self.root.configure(menu=self.menubar)
        try:
            self.root.createcommand("tkAboutDialog", self.show_about_dialog)
        except tk.TclError:
            pass

    def show_about_dialog(self):
        messagebox.showinfo(f"About {APP_NAME}", about_text(), parent=self.root)

    def open_security_preferences(self):
        try:
            subprocess.run(
                ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"]
            )
        except Exception as exc:
            print(f"Error opening System Preferences: {exc}")

    def show_permissions_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Full Disk Access Required")
        dialog.geometry("500x500")
        dialog.minsize(500, 500)
        dialog.transient(self.root)
        dialog.grab_set()
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        ttk.Label(main_frame, text="⚠️", font=("TkDefaultFont", 48)).pack(pady=10)
        ttk.Label(
            main_frame, text="Full Disk Access Required", font=("TkDefaultFont", 14, "bold")
        ).pack(pady=5)
        ttk.Label(
            main_frame,
            text=(
                "This tool only reads the Voice Memos database and never modifies it."
            ),
            wraplength=400,
        ).pack(pady=5)
        instructions = ttk.Frame(main_frame)
        instructions.pack(fill=tk.BOTH, expand=True, pady=10)
        steps = full_disk_access_steps(_is_packaged_app())
        for step in steps:
            ttk.Label(instructions, text=step, wraplength=400).pack(anchor="w", pady=2)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        ttk.Button(
            button_frame,
            text="Open Security Settings",
            command=lambda: [self.open_security_preferences(), dialog.destroy()],
        ).grid(row=0, column=0, padx=5, sticky="e")
        ttk.Button(button_frame, text="Close", command=dialog.destroy).grid(
            row=0, column=1, padx=5, sticky="w"
        )

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        search_frame = ttk.Frame(main_frame)
        search_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0)
        )
        ttk.Checkbutton(
            search_frame,
            text="Include Recently Deleted",
            variable=self.include_deleted_var,
            command=self.load_recordings,
        ).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(search_frame, text="Reload", command=self.load_recordings).pack(
            side=tk.LEFT, padx=(5, 0)
        )
        self.tree = ttk.Treeview(
            main_frame, columns=COLUMNS, show="headings"
        )
        self.tree.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.tree.heading("title", text="Title")
        self.tree.heading("date", text="Date")
        self.tree.heading("duration", text="Duration")
        self.tree.heading("local", text="Local")
        self.tree.heading("status", text="Status")
        self.tree.heading("checked", text="Select ☐")
        self.tree.column("title", width=300)
        self.tree.column("date", width=150)
        self.tree.column("duration", width=80)
        self.tree.column("local", width=80, anchor="center")
        self.tree.column("status", width=130, anchor="center")
        self.tree.column("checked", width=80, anchor="center")
        ttk.Style().configure("Treeview", rowheight=25)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=1, column=2, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=scrollbar.set)
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)
        ttk.Button(left_frame, text="Select All", command=self.select_all).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(left_frame, text="Deselect All", command=self.deselect_all).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Label(left_frame, text="Click checkbox column to select individual items").pack(
            side=tk.LEFT, padx=10
        )
        self.export_button = ttk.Button(
            button_frame, text="Export Selected", command=self.export_selected
        )
        self.export_button.pack(side=tk.RIGHT, padx=5)
        ttk.Checkbutton(button_frame, text="Dry run", variable=self.dry_run_var).pack(
            side=tk.RIGHT
        )
        ttk.Label(main_frame, textvariable=self.status_var).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=(8, 0)
        )
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        self.tree.bind("<Button-1>", self.on_click)

    @staticmethod
    def _display_values(recording):
        date_text = recording.date.strftime("%Y-%m-%d %H:%M:%S") if recording.date else ""
        duration_text = format_duration(recording.duration)
        return str(recording.title), date_text, duration_text

    def _render_keys(self, keys):
        children = self.tree.get_children()
        if children:
            self.tree.delete(*children)
        self.row_keys.clear()
        self.visible_keys = list(keys)
        self.root.title(f"Voice Memos Exporter — {len(self.recordings)} recordings ({len(self.visible_keys)} shown)")
        for key in self.visible_keys:
            recording = self.recordings[key]
            title, date_text, duration_text = self._display_values(recording)
            iid = self.tree.insert(
                "",
                "end",
                values=(
                    title,
                    date_text,
                    duration_text,
                    local_label(self.source_states.get(key)),
                    status_label(recording),
                    "☑" if key in self.selected_keys else "☐",
                ),
            )
            self.row_keys[iid] = key

    def filter_recordings(self, *args):
        search = self.search_var.get()
        matches = core_filter_recordings(
            self.recordings.values(), search=search or None
        )
        self._render_keys([recording.key for recording in matches])

    def load_recordings(self):
        self.db_diagnosis = diagnose_database(self.db_path)
        status = self.db_diagnosis.status
        if status is DbStatus.PERMISSION_DENIED:
            self.recordings = {}
            self.source_states = {}
            self._render_keys([])
            self._set_export_enabled(
                False,
                f"Database unavailable ({status.value}). Export is disabled.",
            )
            self.show_permissions_dialog()
            return
        if status is not DbStatus.OK:
            self.recordings = {}
            self.source_states = {}
            self._render_keys([])
            self._set_export_enabled(
                False,
                f"Database unavailable ({status.value}). Export is disabled.",
            )
            titles = {
                DbStatus.MISSING: "Voice Memos Database Not Found",
                DbStatus.SCHEMA_INCOMPATIBLE: "Unsupported Voice Memos Database Layout",
                DbStatus.LOCKED: "Voice Memos Database Is Busy",
                DbStatus.CORRUPT: "Voice Memos Database Error",
                DbStatus.UNKNOWN: "Voice Memos Database Error",
            }
            detail = self.db_diagnosis.detail
            if status is DbStatus.LOCKED:
                detail = (
                    "Voice Memos or iCloud sync is using the database. "
                    "Quit Voice Memos and try again.\n\n" + detail
                )
            if self.db_diagnosis.exception_type:
                detail += (
                    f"\n\n{self.db_diagnosis.exception_type}: "
                    f"{self.db_diagnosis.exception_message}"
                )
            messagebox.showerror(titles[status], detail)
            return
        try:
            with open_database(self.db_path) as conn:
                recordings, warnings = load_recordings(
                    conn, include_trashed=self.include_deleted_var.get()
                )
            self.recordings = {recording.key: recording for recording in recordings}
            self.source_states = {
                recording.key: resolve_source(
                    self.recordings_path, recording.rel_path
                )[0]
                for recording in self.recordings.values()
            }
            self.selected_keys &= set(self.recordings)
            self.filter_recordings()
            self._set_export_enabled(
                True, f"{len(self.recordings)} recordings loaded."
            )
            if warnings:
                messagebox.showwarning("Recordings Skipped", "\n".join(warnings))
        except Exception as exc:
            self.recordings = {}
            self.source_states = {}
            self._render_keys([])
            self._set_export_enabled(
                False, "Database unavailable (unknown). Export is disabled."
            )
            messagebox.showerror("Database Error", f"{type(exc).__name__}: {exc}")

    def _set_export_enabled(self, enabled, message=""):
        self.export_button.configure(state=(tk.NORMAL if enabled else tk.DISABLED))
        self.status_var.set(message)

    def on_click(self, event):
        if self.tree.identify("region", event.x, event.y) == "cell":
            if self.tree.identify_column(event.x) == CHECK_COLUMN:
                iid = self.tree.identify_row(event.y)
                if iid:
                    self.toggle_item(iid)

    def toggle_item(self, iid):
        key = self.row_keys.get(iid)
        if key is None:
            return
        if key in self.selected_keys:
            self.selected_keys.remove(key)
            checked = "☐"
        else:
            self.selected_keys.add(key)
            checked = "☑"
        self.tree.set(iid, "checked", checked)

    def select_all(self):
        self.selected_keys.update(self.visible_keys)
        children = self.tree.get_children()
        for iid in children:
            self.tree.set(iid, "checked", "☑")
        if children:
            self.tree.selection_set(children)

    def deselect_all(self):
        self.selected_keys.difference_update(self.visible_keys)
        children = self.tree.get_children()
        for iid in children:
            self.tree.set(iid, "checked", "☐")
        if children:
            self.tree.selection_remove(*children)

    def selected_recordings(self):
        return [
            recording
            for key, recording in self.recordings.items()
            if key in self.selected_keys
        ]

    def export_selected(self):
        if self._export_running:
            return
        if self.db_diagnosis is None or self.db_diagnosis.status is not DbStatus.OK:
            return
        targets = self.selected_recordings()
        if not targets:
            messagebox.showwarning("No Selection", "Please select at least one recording to export.")
            return
        export_dir = filedialog.askdirectory(title="Select Export Directory")
        if not export_dir:
            return
        dry_run = self.dry_run_var.get()
        self._export_running = True
        try:
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Dry run..." if dry_run else "Exporting...")
            progress_window.geometry("420x180")
            progress_window.transient(self.root)
            progress_window.grab_set()
            progress_label = ttk.Label(progress_window, text="Preparing export...")
            progress_label.pack(pady=10)
            progress_var = tk.DoubleVar(value=0)
            ttk.Progressbar(
                progress_window, variable=progress_var, maximum=len(targets)
            ).pack(pady=10, padx=20, fill=tk.X)
            cancel_event = threading.Event()

            def request_cancel():
                cancel_event.set()
                cancel_button.configure(state=tk.DISABLED)
                progress_label.configure(text="Cancelling...")

            cancel_button = ttk.Button(
                progress_window, text="Cancel", command=request_cancel
            )
            cancel_button.pack(pady=5)
            progress_window.protocol("WM_DELETE_WINDOW", request_cancel)
        except Exception as exc:
            self._export_running = False
            messagebox.showerror("Export Error", f"{type(exc).__name__}: {exc}")
            return
        events = queue.Queue()

        def finish_progress():
            self._export_running = False
            if progress_window.winfo_exists():
                progress_window.grab_release()
                progress_window.destroy()

        def progress(done, total, title):
            events.put(("progress", done, total, title))

        def worker():
            try:
                summary = self._run_export(
                    targets,
                    export_dir,
                    progress=progress,
                    cancel=cancel_event.is_set,
                    dry_run=dry_run,
                )
                events.put(("done", summary))
            except Exception as exc:
                events.put(("error", type(exc).__name__, str(exc)))

        def poll():
            finished = False
            while True:
                try:
                    event = events.get_nowait()
                except queue.Empty:
                    break
                if event[0] == "progress":
                    _, done, total, title = event
                    progress_var.set(done)
                    progress_label.configure(text=f"{done}/{total}: {title}")
                elif event[0] == "done":
                    summary = event[1]
                    finish_progress()
                    text = "No files were copied (dry run).\n\n" if dry_run else ""
                    text += (
                        f"Total:    {summary.total}\n"
                        f"Exported: {summary.exported}\n"
                        f"Skipped:  {summary.skipped}\n"
                        f"Failed:   {summary.failed}"
                    )
                    if summary.log_path:
                        text += f"\n\nLog: {summary.log_path}"
                    title_prefix = "Dry Run — " if dry_run else ""
                    if summary.failed > 0 or summary.skipped > 0:
                        messagebox.showwarning(
                            f"{title_prefix}Export Partially Complete", text
                        )
                    else:
                        messagebox.showinfo(f"{title_prefix}Export Complete", text)
                    finished = True
                elif event[0] == "error":
                    finish_progress()
                    messagebox.showerror("Export Error", f"{event[1]}: {event[2]}")
                    finished = True
            if not finished and progress_window.winfo_exists():
                self.root.after(100, poll)

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(100, poll)

    def _run_export(self, targets, export_dir, *, progress, cancel, dry_run):
        summary = export_recordings(
            targets,
            export_dir,
            recordings_dir=self.recordings_path,
            progress=progress,
            cancel=cancel,
            dry_run=dry_run,
        )
        if not dry_run:
            summary.log_path = write_log(
                export_dir, summary, db_diagnosis=self.db_diagnosis
            )
        return summary


def main():
    if os.environ.get("VMX_APP_SELFTEST") == "1":
        return _emit_selftest()
    if _TK_IMPORT_ERROR is not None:
        raise RuntimeError("Tkinter is required to run the GUI") from _TK_IMPORT_ERROR
    root = tk.Tk()
    VoiceMemosExporter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
