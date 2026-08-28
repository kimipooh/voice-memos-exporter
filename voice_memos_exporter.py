"""Voice Memos Exporter — local-only Tkinter GUI.

Provenance
----------
Derived from the upstream project ``rudrakabir/voice-memos-exporter``.
Only the upstream UI structure and interaction model are reused here.
All database access and export logic were replaced by this fork's
``vmx_core`` module; no upstream DB or export code remains in this file.

The upstream repository has no clear license file, so the license status of
the upstream-derived UI structure is currently unresolved. This file therefore
lives only on the local branch ``gui/local-app`` and is NOT for publication,
redistribution, or release until that status is resolved.
"""

import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from vmx_core import (
    DEFAULT_DB_PATH,
    DbStatus,
    diagnose_database,
    export_recordings,
    filter_recordings as core_filter_recordings,
    format_duration,
    load_recordings,
    open_database,
    write_log,
)


class VoiceMemosExporter:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Memos Exporter")
        self.root.geometry("1000x600")
        self.root.minsize(800, 400)
        self.db_path = DEFAULT_DB_PATH
        self.recordings_path = os.path.dirname(self.db_path)
        self.recordings = {}
        self.selected_keys = set()
        self.row_keys = {}
        self.visible_keys = []
        self.db_diagnosis = None
        self._export_running = False
        self.search_var = tk.StringVar()
        self.create_widgets()
        self.search_var.trace_add("write", self.filter_recordings)
        self.load_recordings()

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
        instructions = ttk.Frame(main_frame)
        instructions.pack(fill=tk.BOTH, expand=True, pady=10)
        steps = [
            "1. Click 'Open Security Settings' below",
            "2. Click the lock 🔒 icon to make changes",
            "3. Click + to add an application",
            "4. Navigate to and select 'Voice Memos Exporter'",
            "   (the current application you're using)",
            "5. Select the application and click Open",
            "6. Ensure the checkbox next to the application is selected",
            "7. Restart this application",
        ]
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
        self.tree = ttk.Treeview(
            main_frame, columns=("title", "date", "duration", "checked"), show="headings"
        )
        self.tree.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.tree.heading("title", text="Title")
        self.tree.heading("date", text="Date")
        self.tree.heading("duration", text="Duration")
        self.tree.heading("checked", text="Select ☐")
        self.tree.column("title", width=300)
        self.tree.column("date", width=200)
        self.tree.column("duration", width=100)
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
        ttk.Button(button_frame, text="Export Selected", command=self.export_selected).pack(
            side=tk.RIGHT, padx=5
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
                values=(title, date_text, duration_text, "☑" if key in self.selected_keys else "☐"),
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
            self.show_permissions_dialog()
            return
        if status is not DbStatus.OK:
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
                recordings, warnings = load_recordings(conn)
            self.recordings = {recording.key: recording for recording in recordings}
            self.filter_recordings()
            if warnings:
                messagebox.showwarning("Recordings Skipped", "\n".join(warnings))
        except Exception as exc:
            messagebox.showerror("Database Error", f"{type(exc).__name__}: {exc}")

    def on_click(self, event):
        if self.tree.identify("region", event.x, event.y) == "cell":
            if self.tree.identify_column(event.x) == "#4":
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
        targets = self.selected_recordings()
        if not targets:
            messagebox.showwarning("No Selection", "Please select at least one recording to export.")
            return
        export_dir = filedialog.askdirectory(title="Select Export Directory")
        if not export_dir:
            return
        self._export_running = True
        try:
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Exporting...")
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
                summary = export_recordings(
                    targets,
                    export_dir,
                    recordings_dir=self.recordings_path,
                    progress=progress,
                    cancel=cancel_event.is_set,
                )
                summary.log_path = write_log(
                    export_dir, summary, db_diagnosis=self.db_diagnosis
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
                    text = (
                        f"Total:    {summary.total}\n"
                        f"Exported: {summary.exported}\n"
                        f"Skipped:  {summary.skipped}\n"
                        f"Failed:   {summary.failed}"
                    )
                    if summary.log_path:
                        text += f"\n\nLog: {summary.log_path}"
                    if summary.failed > 0 or summary.skipped > 0:
                        messagebox.showwarning("Export Partially Complete", text)
                    else:
                        messagebox.showinfo("Export Complete", text)
                    finished = True
                elif event[0] == "error":
                    finish_progress()
                    messagebox.showerror("Export Error", f"{event[1]}: {event[2]}")
                    finished = True
            if not finished and progress_window.winfo_exists():
                self.root.after(100, poll)

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(100, poll)


def main():
    root = tk.Tk()
    VoiceMemosExporter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
