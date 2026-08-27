import os
import tempfile
import unittest

from vmx_core import unique_destination


class UniqueDestinationTests(unittest.TestCase):
    def test_existing_and_taken_names_increment(self):
        with tempfile.TemporaryDirectory() as export_dir:
            with open(os.path.join(export_dir, "Meeting.m4a"), "wb"):
                pass
            taken = set()
            first = unique_destination(export_dir, "Meeting.m4a", taken)
            second = unique_destination(export_dir, "Meeting.m4a", taken)
            self.assertEqual(os.path.basename(first), "Meeting_1.m4a")
            self.assertEqual(os.path.basename(second), "Meeting_2.m4a")

    def test_parent_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as export_dir:
            with self.assertRaises(ValueError):
                unique_destination(export_dir, "../escape.m4a", set())

    def test_absolute_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as export_dir:
            with self.assertRaises(ValueError):
                unique_destination(export_dir, "/tmp/escape.m4a", set())


if __name__ == "__main__":
    unittest.main()
