from datetime import datetime
import os
import tempfile
import unittest

from tests.fixtures import create_audio
from vmx_core import APPLE_EPOCH_OFFSET, Outcome, Recording, export_recordings, write_log


def recording(index, title=None, date=None, date_epoch=None):
    return Recording(
        key=f"pk:{index}",
        pk=index,
        unique_id=f"uid-{index}",
        rel_path=f"audio-{index}.m4a",
        title=title or f"Recording {index}",
        date=date,
        duration=1.0,
        date_epoch=date_epoch,
    )


class ExportTests(unittest.TestCase):
    def test_missing_source_fails_and_next_item_continues(self):
        with tempfile.TemporaryDirectory() as recordings_dir, tempfile.TemporaryDirectory() as export_dir:
            create_audio(recordings_dir, "audio-2.m4a")
            summary = export_recordings(
                [recording(1), recording(2)], export_dir, recordings_dir=recordings_dir
            )
            self.assertEqual((summary.exported, summary.failed), (1, 1))
            failed = summary.records[0]
            self.assertEqual(failed.outcome, Outcome.FAILED)
            self.assertEqual(failed.error_type, "FileNotFoundError")
            self.assertEqual(failed.error_message, "Source file missing")

    def test_icloud_placeholder_is_skipped_and_next_item_continues(self):
        with tempfile.TemporaryDirectory() as recordings_dir, tempfile.TemporaryDirectory() as export_dir:
            create_audio(recordings_dir, ".audio-1.m4a.icloud")
            create_audio(recordings_dir, "audio-2.m4a")
            summary = export_recordings(
                [recording(1), recording(2)], export_dir, recordings_dir=recordings_dir
            )
            self.assertEqual((summary.exported, summary.skipped, summary.failed), (1, 1, 0))
            self.assertEqual(summary.records[0].outcome, Outcome.SKIPPED_NOT_DOWNLOADED)

    def test_one_failure_among_one_hundred_does_not_stop_export(self):
        with tempfile.TemporaryDirectory() as recordings_dir, tempfile.TemporaryDirectory() as export_dir:
            items = [recording(index) for index in range(100)]
            for item in items[1:]:
                create_audio(recordings_dir, item.rel_path)
            summary = export_recordings(items, export_dir, recordings_dir=recordings_dir)
            self.assertEqual((summary.total, summary.exported, summary.failed), (100, 99, 1))

    def test_duplicate_metadata_exports_distinct_files(self):
        with tempfile.TemporaryDirectory() as recordings_dir, tempfile.TemporaryDirectory() as export_dir:
            items = [recording(1, "Same"), recording(2, "Same")]
            for item in items:
                create_audio(recordings_dir, item.rel_path, item.key.encode())
            summary = export_recordings(items, export_dir, recordings_dir=recordings_dir)
            names = [os.path.basename(item.dest_path) for item in summary.records]
            self.assertEqual(names, ["Same.m4a", "Same_1.m4a"])
            self.assertEqual(summary.exported, 2)

    def test_recording_date_sets_destination_mtime(self):
        with tempfile.TemporaryDirectory() as recordings_dir, tempfile.TemporaryDirectory() as export_dir:
            expected_timestamp = APPLE_EPOCH_OFFSET + 12345
            item = recording(
                1,
                date=datetime.fromtimestamp(expected_timestamp - 3600),
                date_epoch=expected_timestamp,
            )
            create_audio(recordings_dir, item.rel_path)
            summary = export_recordings([item], export_dir, recordings_dir=recordings_dir)
            self.assertAlmostEqual(os.path.getmtime(summary.records[0].dest_path), expected_timestamp, places=3)

    def test_cancel_marks_all_remaining_items_skipped(self):
        with tempfile.TemporaryDirectory() as recordings_dir, tempfile.TemporaryDirectory() as export_dir:
            items = [recording(index) for index in range(3)]
            progress = []
            summary = export_recordings(
                items,
                export_dir,
                recordings_dir=recordings_dir,
                cancel=lambda: True,
                progress=lambda done, total, title: progress.append((done, total, title)),
            )
            self.assertEqual((summary.total, summary.skipped, summary.failed), (3, 3, 0))
            self.assertTrue(
                all(item.outcome is Outcome.SKIPPED_CANCELLED for item in summary.records)
            )
            self.assertEqual(progress[-1][:2], (3, 3))

    def test_log_is_only_written_for_incomplete_export(self):
        with tempfile.TemporaryDirectory() as recordings_dir, tempfile.TemporaryDirectory() as export_dir:
            item = recording(1)
            create_audio(recordings_dir, item.rel_path)
            successful = export_recordings([item], export_dir, recordings_dir=recordings_dir)
            self.assertIsNone(write_log(export_dir, successful))

            failed = export_recordings(
                [recording(2)], export_dir, recordings_dir=recordings_dir
            )
            log_path = write_log(export_dir, failed)
            self.assertTrue(os.path.isfile(log_path))
            with open(log_path, encoding="utf-8") as log_file:
                contents = log_file.read()
            self.assertIn('"recording_key": "pk:2"', contents)
            self.assertIn('"error_type": "FileNotFoundError"', contents)


if __name__ == "__main__":
    unittest.main()
