import os
import unittest
from unittest import mock

from vmx_core import Recording

try:
    import tkinter as tk
    from voice_memos_exporter import VoiceMemosExporter
except (ImportError, ModuleNotFoundError):
    tk = None
    VoiceMemosExporter = None


def recordings():
    return [
        Recording(f"pk:{index}", index, None, f"{index}.m4a", f"Title {index}", None, 1)
        for index in range(3)
    ]


class SelectionModelTests(unittest.TestCase):
    def test_stable_keys_survive_filter_rebuild(self):
        items = recordings()
        recording_map = {item.key: item for item in items}
        selected_keys = {items[0].key, items[2].key}
        visible = [key for key, item in recording_map.items() if "xxx" in item.title.lower()]
        self.assertEqual(visible, [])
        visible = [key for key, item in recording_map.items() if "" in item.title.lower()]
        self.assertEqual(len(visible), 3)
        targets = [item for key, item in recording_map.items() if key in selected_keys]
        self.assertEqual(targets, [items[0], items[2]])


@unittest.skipIf(tk is None, "Tk GUI unavailable")
class SelectionGuiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
            self.root.withdraw()
        except tk.TclError as exc:
            self.skipTest(f"Tk GUI unavailable: {exc}")

    def tearDown(self):
        if hasattr(self, "root"):
            self.root.destroy()

    def test_tree_iids_change_but_selected_recordings_do_not(self):
        missing_db = os.path.join(os.sep, "definitely-not-a-real-voice-memos-db")
        with mock.patch("voice_memos_exporter.DEFAULT_DB_PATH", missing_db), mock.patch(
            "voice_memos_exporter.messagebox.showerror"
        ):
            app = VoiceMemosExporter(self.root)
        items = recordings()
        app.recordings = {item.key: item for item in items}
        app._render_keys(app.recordings)
        initial_iids = app.tree.get_children()
        app.toggle_item(initial_iids[0])
        app.toggle_item(initial_iids[2])
        app.search_var.set("xxx")
        self.assertEqual(app.tree.get_children(), ())
        app.search_var.set("")
        rebuilt_iids = app.tree.get_children()
        self.assertNotEqual(initial_iids, rebuilt_iids)
        self.assertEqual(app.selected_recordings(), [items[0], items[2]])


if __name__ == "__main__":
    unittest.main()
