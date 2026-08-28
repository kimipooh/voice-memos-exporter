import os
import unittest
from unittest import mock

from vmx_core import Recording, SourceState

try:
    import tkinter as tk
    import voice_memos_exporter
    from voice_memos_exporter import VoiceMemosExporter
except (ImportError, ModuleNotFoundError):
    tk = None
    voice_memos_exporter = None
    VoiceMemosExporter = None


@unittest.skipIf(voice_memos_exporter is None, "GUI module unavailable")
class LabelTests(unittest.TestCase):
    def test_local_label_maps_source_states(self):
        self.assertEqual(voice_memos_exporter.local_label(SourceState.AVAILABLE), "Yes")
        self.assertEqual(
            voice_memos_exporter.local_label(SourceState.NOT_DOWNLOADED), "iCloud"
        )
        self.assertEqual(voice_memos_exporter.local_label(SourceState.MISSING), "Missing")
        self.assertEqual(voice_memos_exporter.local_label(object()), "?")

    def test_status_label_distinguishes_recently_deleted(self):
        active = Recording("pk:1", 1, None, "one.m4a", "One", None, 1)
        deleted = Recording(
            "pk:2", 2, None, "two.m4a", "Two", None, 2, is_trashed=True
        )
        self.assertEqual(voice_memos_exporter.status_label(active), "Active")
        self.assertEqual(
            voice_memos_exporter.status_label(deleted), "Recently Deleted"
        )


@unittest.skipIf(voice_memos_exporter is None, "GUI module unavailable")
class AboutTextTests(unittest.TestCase):
    def test_about_text_has_attribution_and_local_use_terms(self):
        text = voice_memos_exporter.about_text()

        self.assertIn("rudrakabir", text)
        self.assertIn("Kimiya Kitani", text)
        self.assertIn("Version 1.0.0", text)
        self.assertIn("Not for redistribution.", text)
        for license_name in ("MIT", "GPL", "Apache"):
            self.assertNotIn(license_name, text)
        self.assertLess(text.index("rudrakabir"), text.index("Kimiya Kitani"))


@unittest.skipIf(tk is None, "Tk GUI unavailable")
class GuiViewTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError as exc:
            self.skipTest(f"Tk GUI unavailable: {exc}")

    def tearDown(self):
        if hasattr(self, "root"):
            self.root.destroy()

    def create_app(self):
        missing_db = os.path.join(os.sep, "definitely-not-a-real-voice-memos-db")
        with mock.patch(
            "voice_memos_exporter.DEFAULT_DB_PATH", missing_db
        ), mock.patch("voice_memos_exporter.messagebox.showerror"):
            return VoiceMemosExporter(self.root)

    def test_rows_render_six_values_with_cached_local_and_status(self):
        app = self.create_app()
        active = Recording("pk:1", 1, None, "one.m4a", "One", None, 65)
        deleted = Recording(
            "pk:2", 2, None, "two.m4a", "Two", None, None, is_trashed=True
        )
        app.recordings = {active.key: active, deleted.key: deleted}
        app.source_states = {
            active.key: SourceState.AVAILABLE,
            deleted.key: SourceState.NOT_DOWNLOADED,
        }

        app._render_keys(app.recordings)

        rows = [app.tree.item(iid, "values") for iid in app.tree.get_children()]
        self.assertEqual(
            rows,
            [
                ("One", "", "1:05", "Yes", "Active", "☐"),
                ("Two", "", "-", "iCloud", "Recently Deleted", "☐"),
            ],
        )

    def test_application_menu_has_exactly_one_about_entry(self):
        app = self.create_app()

        self.assertIsNotNone(app.app_menu)
        self.assertEqual(str(self.root.cget("menu")), str(app.menubar))
        self.assertEqual(app.app_menu.winfo_name(), "apple")
        labels = [
            app.app_menu.entrycget(index, "label")
            for index in range(app.app_menu.index("end") + 1)
            if app.app_menu.type(index) != "separator"
        ]
        self.assertEqual(
            [label for label in labels if "About" in label],
            [f"About {voice_memos_exporter.APP_NAME}"],
        )

    def test_about_menu_entry_shows_attribution_dialog(self):
        app = self.create_app()

        with mock.patch("voice_memos_exporter.messagebox.showinfo") as showinfo:
            app.app_menu.invoke(0)

        showinfo.assert_called_once()
        title, message = showinfo.call_args.args
        self.assertEqual(title, f"About {voice_memos_exporter.APP_NAME}")
        self.assertEqual(message, voice_memos_exporter.about_text())

    def test_tk_about_hook_remains_registered_as_fallback(self):
        self.create_app()

        self.assertEqual(
            self.root.tk.eval("info commands tkAboutDialog"), "tkAboutDialog"
        )
        with mock.patch("voice_memos_exporter.messagebox.showinfo") as showinfo:
            self.root.tk.eval("tkAboutDialog")

        showinfo.assert_called_once()
        self.assertEqual(
            showinfo.call_args.args[1], voice_memos_exporter.about_text()
        )

    def test_check_column_and_toggle_use_last_column(self):
        app = self.create_app()
        recording = Recording("pk:1", 1, None, "one.m4a", "One", None, 1)
        app.recordings = {recording.key: recording}
        app.source_states = {recording.key: SourceState.MISSING}
        app._render_keys(app.recordings)
        iid = app.tree.get_children()[0]

        self.assertEqual(voice_memos_exporter.CHECK_COLUMN, "#6")
        self.assertEqual(app.tree.item(iid, "values")[-1], "☐")
        app.toggle_item(iid)
        self.assertEqual(app.tree.item(iid, "values")[-1], "☑")

    def test_export_is_disabled_after_failed_load(self):
        app = self.create_app()

        self.assertEqual(str(app.export_button["state"]), "disabled")
        self.assertTrue(app.status_var.get())

    def test_include_recently_deleted_reload_passes_include_trashed(self):
        app = self.create_app()
        items = [
            Recording("pk:1", 1, None, "one.m4a", "One", None, 1),
            Recording("pk:2", 2, None, "two.m4a", "Two", None, 2, is_trashed=True),
        ]
        app.selected_keys = {"pk:1", "pk:gone"}
        app.include_deleted_var.set(True)

        diagnosis = mock.Mock(status=voice_memos_exporter.DbStatus.OK)
        with mock.patch(
            "voice_memos_exporter.diagnose_database", return_value=diagnosis
        ), mock.patch("voice_memos_exporter.open_database"), mock.patch(
            "voice_memos_exporter.load_recordings", return_value=(items, [])
        ) as load_mock, mock.patch(
            "voice_memos_exporter.resolve_source",
            return_value=(SourceState.AVAILABLE, "/src"),
        ):
            app.load_recordings()

        self.assertTrue(load_mock.call_args.kwargs["include_trashed"])
        self.assertEqual(app.selected_keys, {"pk:1"})
        self.assertEqual(str(app.export_button["state"]), "normal")
        self.assertEqual(len(app.tree.get_children()), 2)

    def test_run_export_dry_run_skips_log(self):
        app = self.create_app()
        summary = mock.Mock(log_path=None)
        progress = mock.Mock()
        cancel = mock.Mock()
        targets = [mock.Mock()]

        with mock.patch(
            "voice_memos_exporter.export_recordings", return_value=summary
        ) as export_mock, mock.patch("voice_memos_exporter.write_log") as log_mock:
            result = app._run_export(
                targets,
                "/tmp/export",
                progress=progress,
                cancel=cancel,
                dry_run=True,
            )

        self.assertIs(result, summary)
        export_mock.assert_called_once_with(
            targets,
            "/tmp/export",
            recordings_dir=app.recordings_path,
            progress=progress,
            cancel=cancel,
            dry_run=True,
        )
        log_mock.assert_not_called()

    def test_run_export_writes_and_assigns_log(self):
        app = self.create_app()
        summary = mock.Mock(log_path=None)
        progress = mock.Mock()
        cancel = mock.Mock()
        targets = [mock.Mock()]

        with mock.patch(
            "voice_memos_exporter.export_recordings", return_value=summary
        ) as export_mock, mock.patch(
            "voice_memos_exporter.write_log", return_value="/tmp/export/result.log"
        ) as log_mock:
            result = app._run_export(
                targets,
                "/tmp/export",
                progress=progress,
                cancel=cancel,
                dry_run=False,
            )

        self.assertIs(result, summary)
        export_mock.assert_called_once_with(
            targets,
            "/tmp/export",
            recordings_dir=app.recordings_path,
            progress=progress,
            cancel=cancel,
            dry_run=False,
        )
        log_mock.assert_called_once_with(
            "/tmp/export", summary, db_diagnosis=app.db_diagnosis
        )
        self.assertEqual(summary.log_path, "/tmp/export/result.log")


if __name__ == "__main__":
    unittest.main()
