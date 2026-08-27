import contextlib
from datetime import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import export_voice_memos
import vmx_core
from tests.fixtures import create_audio, create_database


def row(index, title, rel_path=None, date=12345, duration=12.5, eviction_date=None):
    return (
        index,
        f"uid-{index}",
        rel_path or f"audio-{index}.m4a",
        title,
        None,
        date,
        duration,
        eviction_date,
    )


def active_and_trash_rows():
    return [
        *[row(index, f"Active {index}") for index in range(1, 6)],
        *[row(index, f"Trash {index}", eviction_date=800000000 + index) for index in range(6, 10)],
    ]


def apple_date(value):
    return value.timestamp() - vmx_core.APPLE_EPOCH_OFFSET


def digest(path):
    with open(path, "rb") as source:
        return hashlib.sha256(source.read()).hexdigest()


class CliTests(unittest.TestCase):
    def invoke(self, arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = export_voice_memos.main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def make_fixture(self, directory, rows):
        db_path = create_database(directory, rows)
        for item in rows:
            create_audio(directory, item[2], str(item[0]).encode())
        return db_path

    def test_help_subprocess(self):
        result = subprocess.run(
            [sys.executable, "export_voice_memos.py", "--help"],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--list", result.stdout)
        self.assertIn("--dry-run", result.stdout)
        self.assertIn("--include-trash", result.stdout)
        self.assertIn("--from DATE", result.stdout)
        self.assertIn("--to DATE", result.stdout)
        self.assertIn("YYYY-MM-DD HH:MM", result.stdout)
        self.assertIn("includes the entire", result.stdout)

    def test_list_excludes_trash_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, active_and_trash_rows())
            code, stdout, _ = self.invoke(["--list", "--db", db_path])
            self.assertEqual(code, 0)
            self.assertIn("Total recordings: 5", stdout)
            self.assertNotIn("Trash 6", stdout)
            self.assertNotIn("STATUS", stdout)

    def test_list_include_trash_shows_all_with_status(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, active_and_trash_rows())
            code, stdout, _ = self.invoke(
                ["--list", "--include-trash", "--db", db_path]
            )
            self.assertEqual(code, 0)
            self.assertIn("Total recordings: 9", stdout)
            self.assertIn("STATUS", stdout)
            self.assertIn("active", stdout)
            self.assertIn("trash", stdout)

    def test_all_excludes_trash_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, active_and_trash_rows())
            output = os.path.join(directory, "output")
            code, _, _ = self.invoke(["--all", "--output", output, "--db", db_path])
            self.assertEqual(code, 0)
            self.assertEqual(len(os.listdir(output)), 5)
            self.assertFalse(os.path.exists(os.path.join(output, "Trash 6.m4a")))

    def test_all_include_trash_exports_all(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, active_and_trash_rows())
            output = os.path.join(directory, "output")
            code, _, _ = self.invoke(
                ["--all", "--include-trash", "--output", output, "--db", db_path]
            )
            self.assertEqual(code, 0)
            self.assertEqual(len(os.listdir(output)), 9)
            self.assertTrue(os.path.isfile(os.path.join(output, "Trash 6.m4a")))

    def test_search_excludes_matching_trash_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, active_and_trash_rows())
            output = os.path.join(directory, "output")
            code, _, stderr = self.invoke(
                ["--search", "Trash 6", "--output", output, "--db", db_path]
            )
            self.assertEqual(code, 1)
            self.assertIn("No recordings matched", stderr)
            self.assertFalse(os.path.exists(output))

    def test_search_include_trash_exports_match(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, active_and_trash_rows())
            output = os.path.join(directory, "output")
            code, _, _ = self.invoke(
                [
                    "--search",
                    "Trash 6",
                    "--include-trash",
                    "--output",
                    output,
                    "--db",
                    db_path,
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual(os.listdir(output), ["Trash 6.m4a"])

    def test_dry_run_respects_include_trash(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, active_and_trash_rows())
            output = os.path.join(directory, "output")
            code, stdout, _ = self.invoke(
                ["--all", "--dry-run", "--output", output, "--db", db_path]
            )
            self.assertEqual(code, 0)
            self.assertIn("Total:    5", stdout)
            self.assertNotIn("Trash 6", stdout)
            code, stdout, _ = self.invoke(
                [
                    "--all",
                    "--dry-run",
                    "--include-trash",
                    "--output",
                    output,
                    "--db",
                    db_path,
                ]
            )
            self.assertEqual(code, 0)
            self.assertIn("Total:    9", stdout)
            self.assertIn("Trash 6", stdout)
            self.assertFalse(os.path.exists(output))

    def test_json_adds_status_field(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, active_and_trash_rows())
            code, stdout, _ = self.invoke(
                ["--list", "--json", "--include-trash", "--db", db_path]
            )
            payload = json.loads(stdout)
            self.assertEqual(code, 0)
            self.assertEqual(len(payload), 9)
            self.assertEqual(
                {item["status"] for item in payload}, {"active", "trash"}
            )

    def test_list_text_includes_count_and_titles(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [row(1, "First"), row(2, "Second")]
            db_path = self.make_fixture(directory, rows)
            code, stdout, _ = self.invoke(["--list", "--db", db_path])
            self.assertEqual(code, 0)
            self.assertIn("Total recordings: 2", stdout)
            self.assertIn("First", stdout)
            self.assertIn("Second", stdout)

    def test_list_json_is_valid_and_has_local_values(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Available")])
            code, stdout, _ = self.invoke(["--list", "--json", "--db", db_path])
            payload = json.loads(stdout)
            self.assertEqual(code, 0)
            self.assertEqual(len(payload), 1)
            self.assertIn(payload[0]["local"], {"yes", "icloud", "missing"})

    def test_list_search_without_matches_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Meeting")])
            code, stdout, _ = self.invoke(
                ["--list", "--search", "no-such-title", "--db", db_path]
            )
            self.assertEqual(code, 0)
            self.assertIn("(matched: 0)", stdout)

    def test_list_json_search_without_matches_returns_empty_array(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Meeting")])
            code, stdout, _ = self.invoke(
                ["--list", "--json", "--search", "no-such-title", "--db", db_path]
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout), [])

    def test_all_exports_every_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "First"), row(2, "Second")])
            output = os.path.join(directory, "output")
            code, _, _ = self.invoke(["--all", "--output", output, "--db", db_path])
            self.assertEqual(code, 0)
            self.assertEqual(set(os.listdir(output)), {"First.m4a", "Second.m4a"})

    def test_search_exports_only_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Interview Hanoi"), row(2, "Meeting")])
            output = os.path.join(directory, "output")
            code, _, _ = self.invoke(
                ["--search", "hAnOi", "--output", output, "--db", db_path]
            )
            self.assertEqual(code, 0)
            self.assertEqual(os.listdir(output), ["Interview Hanoi.m4a"])

    def test_search_without_matches_creates_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Meeting")])
            output = os.path.join(directory, "output")
            code, _, stderr = self.invoke(
                ["--search", "no-such-title", "--output", output, "--db", db_path]
            )
            self.assertEqual(code, 1)
            self.assertFalse(os.path.exists(output))
            self.assertIn("No recordings matched", stderr)

    def test_dry_run_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Meeting")])
            output = os.path.join(directory, "output")
            code, stdout, _ = self.invoke(
                ["--all", "--dry-run", "--output", output, "--db", db_path]
            )
            self.assertEqual(code, 0)
            self.assertFalse(os.path.exists(output))
            self.assertIn("dry-run", stdout)

    def test_partial_failure_exports_available_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [row(1, "Missing"), row(2, "Available")]
            db_path = create_database(directory, rows)
            create_audio(directory, rows[1][2])
            output = os.path.join(directory, "output")
            code, stdout, _ = self.invoke(["--all", "-o", output, "--db", db_path])
            self.assertEqual(code, 2)
            self.assertTrue(os.path.isfile(os.path.join(output, "Available.m4a")))
            self.assertIn("Failed:   1", stdout)

    def test_numeric_titles_export(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [row(index, title) for index, title in enumerate(("2026", "123", "001"), 1)]
            db_path = self.make_fixture(directory, rows)
            output = os.path.join(directory, "output")
            code, _, _ = self.invoke(["--all", "-o", output, "--db", db_path])
            self.assertEqual(code, 0)
            self.assertEqual(set(os.listdir(output)), {"2026.m4a", "123.m4a", "001.m4a"})

    def test_slash_title_does_not_create_subdirectory(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Interview / Hanoi")])
            output = os.path.join(directory, "output")
            code, _, _ = self.invoke(["--all", "-o", output, "--db", db_path])
            self.assertEqual(code, 0)
            self.assertEqual(os.listdir(output), ["Interview - Hanoi.m4a"])
            self.assertFalse(any(os.path.isdir(os.path.join(output, name)) for name in os.listdir(output)))

    def test_unicode_titles_remain_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            titles = ["会議メモ", "Phỏng vấn Hà Nội", "บันทึกการประชุม"]
            db_path = self.make_fixture(directory, [row(index, title) for index, title in enumerate(titles, 1)])
            output = os.path.join(directory, "output")
            code, _, _ = self.invoke(["--all", "-o", output, "--db", db_path])
            self.assertEqual(code, 0)
            self.assertEqual(set(os.listdir(output)), {f"{title}.m4a" for title in titles})

    def test_duplicate_titles_get_unique_names(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(index, "X") for index in range(1, 4)])
            output = os.path.join(directory, "output")
            code, _, _ = self.invoke(["--all", "-o", output, "--db", db_path])
            self.assertEqual(code, 0)
            self.assertEqual(set(os.listdir(output)), {"X.m4a", "X_1.m4a", "X_2.m4a"})

    def test_icloud_is_listed_and_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [row(1, "Cloud", "cloud.m4a"), row(2, "Local", "local.m4a")]
            db_path = create_database(directory, rows)
            create_audio(directory, ".cloud.m4a.icloud")
            create_audio(directory, "local.m4a")
            list_code, stdout, _ = self.invoke(["--list", "--db", db_path])
            self.assertEqual(list_code, 0)
            self.assertIn("icloud", stdout)
            output = os.path.join(directory, "output")
            code, _, _ = self.invoke(["--all", "-o", output, "--db", db_path])
            self.assertEqual(code, 2)
            self.assertTrue(os.path.isfile(os.path.join(output, "Local.m4a")))

    def test_database_digest_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Meeting")])
            before = digest(db_path)
            code, _, _ = self.invoke(["--list", "--db", db_path])
            self.assertEqual(code, 0)
            self.assertEqual(digest(db_path), before)

    def test_output_is_required_for_export(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Meeting")])
            code, _, stderr = self.invoke(["--all", "--db", db_path])
            self.assertEqual(code, 1)
            self.assertIn("usage:", stderr)

    def test_action_is_required(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Meeting")])
            code, _, stderr = self.invoke(["--db", db_path])
            self.assertEqual(code, 1)
            self.assertIn("usage:", stderr)

    def test_search_handles_unicode_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Café Hanoi")])
            code, stdout, _ = self.invoke(["--list", "--search", "Cafe\u0301", "--db", db_path])
            self.assertEqual(code, 0)
            self.assertIn("matched: 1", stdout)

    def test_control_characters_do_not_split_list_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = self.make_fixture(directory, [row(1, "Line one\nLine two")])
            code, stdout, _ = self.invoke(["--list", "--db", db_path])
            self.assertEqual(code, 0)
            self.assertIn("Line one Line two", stdout)

    def test_from_date_only_includes_same_day_and_later(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [
                row(1, "Before", date=apple_date(datetime(2026, 7, 30, 23, 59))),
                row(2, "At midnight", date=apple_date(datetime(2026, 7, 31, 0, 0))),
                row(3, "Later", date=apple_date(datetime(2026, 8, 1, 9, 0))),
            ]
            db_path = self.make_fixture(directory, rows)
            code, stdout, _ = self.invoke(
                ["--list", "--from", "2026-07-31", "--db", db_path]
            )
            self.assertEqual(code, 0)
            self.assertIn("Total recordings: 2", stdout)
            self.assertNotIn("Before", stdout)
            self.assertIn("At midnight", stdout)
            self.assertIn("Later", stdout)

    def test_to_date_only_includes_entire_day(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [
                row(1, "Late July", date=apple_date(datetime(2026, 7, 31, 23, 59, 59))),
                row(2, "August", date=apple_date(datetime(2026, 8, 1, 0, 0))),
            ]
            db_path = self.make_fixture(directory, rows)
            code, stdout, _ = self.invoke(
                ["--list", "--to", "2026-07-31", "--db", db_path]
            )
            self.assertEqual(code, 0)
            self.assertIn("Total recordings: 1", stdout)
            self.assertIn("Late July", stdout)
            self.assertNotIn("August", stdout)

    def test_from_and_to_select_only_range(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [
                row(1, "June", date=apple_date(datetime(2026, 6, 30, 23, 59))),
                row(2, "July", date=apple_date(datetime(2026, 7, 15, 12, 0))),
                row(3, "August", date=apple_date(datetime(2026, 8, 1, 0, 0))),
            ]
            db_path = self.make_fixture(directory, rows)
            code, stdout, _ = self.invoke(
                [
                    "--list",
                    "--from",
                    "2026-07-01",
                    "--to",
                    "2026-07-31",
                    "--db",
                    db_path,
                ]
            )
            self.assertEqual(code, 0)
            self.assertIn("Total recordings: 1", stdout)
            self.assertIn("July", stdout)
            self.assertNotIn("June", stdout)
            self.assertNotIn("August", stdout)

    def test_datetime_formats_apply_exact_times(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [
                row(1, "Too early", date=apple_date(datetime(2026, 7, 13, 11, 59, 59))),
                row(2, "In range", date=apple_date(datetime(2026, 7, 13, 12, 0))),
                row(3, "Too late", date=apple_date(datetime(2026, 7, 13, 16, 0, 1))),
            ]
            db_path = self.make_fixture(directory, rows)
            code, stdout, _ = self.invoke(
                [
                    "--list",
                    "--from",
                    "2026-07-13 12:00",
                    "--to",
                    "2026-07-13 16:00:00",
                    "--db",
                    db_path,
                ]
            )
            self.assertEqual(code, 0)
            self.assertIn("In range", stdout)
            self.assertNotIn("Too early", stdout)
            self.assertNotIn("Too late", stdout)

    def test_invalid_date_formats_are_fatal(self):
        for option, value in (
            ("--from", "2026/07/01"),
            ("--from", "yesterday"),
            ("--to", "2026-13-99"),
        ):
            with self.subTest(option=option, value=value):
                code, _, stderr = self.invoke(["--list", option, value])
                self.assertEqual(code, 1)
                self.assertIn("must use YYYY-MM-DD", stderr)

    def test_from_after_to_is_fatal(self):
        code, _, stderr = self.invoke(
            ["--list", "--from", "2026-08-01", "--to", "2026-07-01"]
        )
        self.assertEqual(code, 1)
        self.assertIn("--from must be earlier than or equal to --to", stderr)

    def test_exact_from_and_to_boundaries_are_inclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            boundary = datetime(2026, 7, 13, 12, 0)
            db_path = self.make_fixture(
                directory, [row(1, "Boundary", date=apple_date(boundary))]
            )
            code, stdout, _ = self.invoke(
                [
                    "--list",
                    "--from",
                    "2026-07-13 12:00",
                    "--to",
                    "2026-07-13 12:00",
                    "--db",
                    db_path,
                ]
            )
            self.assertEqual(code, 0)
            self.assertIn("Total recordings: 1", stdout)
            self.assertIn("Boundary", stdout)

    def test_search_and_date_filters_are_combined(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [
                row(1, "Chiang Mai July", date=apple_date(datetime(2026, 7, 10))),
                row(2, "Other July", date=apple_date(datetime(2026, 7, 11))),
                row(3, "Chiang Mai August", date=apple_date(datetime(2026, 8, 10))),
            ]
            db_path = self.make_fixture(directory, rows)
            code, stdout, _ = self.invoke(
                [
                    "--list",
                    "--search",
                    "chiang mai",
                    "--from",
                    "2026-07-01",
                    "--to",
                    "2026-07-31",
                    "--db",
                    db_path,
                ]
            )
            self.assertEqual(code, 0)
            self.assertIn("Total recordings: 2 (matched: 1)", stdout)
            self.assertIn("Chiang Mai July", stdout)
            self.assertNotIn("Other July", stdout)
            self.assertNotIn("Chiang Mai August", stdout)

    def test_include_trash_and_date_filters_are_combined(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [
                row(1, "Active July", date=apple_date(datetime(2026, 7, 10))),
                row(
                    2,
                    "Trash July",
                    date=apple_date(datetime(2026, 7, 11)),
                    eviction_date=1,
                ),
                row(
                    3,
                    "Trash August",
                    date=apple_date(datetime(2026, 8, 11)),
                    eviction_date=1,
                ),
            ]
            db_path = self.make_fixture(directory, rows)
            code, stdout, _ = self.invoke(
                [
                    "--list",
                    "--include-trash",
                    "--from",
                    "2026-07-01",
                    "--to",
                    "2026-07-31",
                    "--db",
                    db_path,
                ]
            )
            self.assertEqual(code, 0)
            self.assertIn("Total recordings: 2", stdout)
            self.assertIn("Active July", stdout)
            self.assertIn("Trash July", stdout)
            self.assertNotIn("Trash August", stdout)

    def test_dry_run_with_date_writes_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [
                row(1, "July", date=apple_date(datetime(2026, 7, 10))),
                row(2, "August", date=apple_date(datetime(2026, 8, 10))),
            ]
            db_path = self.make_fixture(directory, rows)
            output = os.path.join(directory, "output")
            code, stdout, _ = self.invoke(
                [
                    "--all",
                    "--dry-run",
                    "--from",
                    "2026-07-01",
                    "--to",
                    "2026-07-31",
                    "--output",
                    output,
                    "--db",
                    db_path,
                ]
            )
            self.assertEqual(code, 0)
            self.assertIn("Total:    1", stdout)
            self.assertIn("July", stdout)
            self.assertNotIn("August", stdout)
            self.assertFalse(os.path.exists(output))

    def test_json_contains_only_date_filtered_recordings(self):
        with tempfile.TemporaryDirectory() as directory:
            rows = [
                row(1, "July", date=apple_date(datetime(2026, 7, 10))),
                row(2, "August", date=apple_date(datetime(2026, 8, 10))),
            ]
            db_path = self.make_fixture(directory, rows)
            code, stdout, _ = self.invoke(
                [
                    "--list",
                    "--json",
                    "--from",
                    "2026-07-01",
                    "--to",
                    "2026-07-31",
                    "--db",
                    db_path,
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual([item["title"] for item in json.loads(stdout)], ["July"])


if __name__ == "__main__":
    unittest.main()
