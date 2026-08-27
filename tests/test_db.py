import hashlib
import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from tests.fixtures import create_database
from vmx_core import (
    DbStatus,
    connect_readonly,
    diagnose_database,
    load_recordings,
    open_database,
)


def digest(path):
    value = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            value.update(chunk)
    return value.hexdigest()


class DatabaseTests(unittest.TestCase):
    def test_connection_is_read_only_and_load_does_not_modify_database(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = create_database(
                directory,
                [(1, "one", "one.m4a", "One", None, 10, 20, None)],
            )
            before = (os.stat(db_path).st_mtime_ns, digest(db_path))
            conn = connect_readonly(db_path)
            load_recordings(conn)
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("INSERT INTO ZCLOUDRECORDING (ZPATH) VALUES ('bad.m4a')")
            conn.close()
            after = (os.stat(db_path).st_mtime_ns, digest(db_path))
            self.assertEqual(before, after)

    def test_null_and_non_numeric_values_do_not_abort_load(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = create_database(
                directory,
                [
                    (1, "one", "one.m4a", "One", None, None, None, None),
                    (2, "two", "two.m4a", "Two", None, "bad", "bad", None),
                ],
            )
            with connect_readonly(db_path) as conn:
                recordings, warnings = load_recordings(conn)
            self.assertEqual(len(recordings), 2)
            self.assertTrue(all(item.date is None and item.duration is None for item in recordings))
            self.assertEqual(warnings, [])

    def test_empty_paths_are_excluded_with_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = create_database(
                directory,
                [
                    (1, "one", None, "One", None, 0, 1, None),
                    (2, "two", "", "Two", None, 0, 1, None),
                    (3, "three", "three.m4a", "Three", None, 0, 1, None),
                ],
            )
            with connect_readonly(db_path) as conn:
                recordings, warnings = load_recordings(conn)
            self.assertEqual(len(recordings), 1)
            self.assertIn("2 recording(s)", warnings[0])

    def test_missing_table_is_schema_incompatible(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = os.path.join(directory, "empty.db")
            sqlite3.connect(db_path).close()
            self.assertEqual(diagnose_database(db_path).status, DbStatus.SCHEMA_INCOMPATIBLE)

    def test_missing_file_is_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                diagnose_database(os.path.join(directory, "missing.db")).status,
                DbStatus.MISSING,
            )

    def test_key_falls_back_without_primary_key_column(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = os.path.join(directory, "fallback.db")
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE ZCLOUDRECORDING (ZUNIQUEID TEXT, ZPATH TEXT)")
            conn.executemany(
                "INSERT INTO ZCLOUDRECORDING VALUES (?, ?)",
                [("uid-one", "one.m4a"), (None, "two.m4a")],
            )
            conn.commit()
            conn.close()
            with connect_readonly(db_path) as conn:
                recordings, _ = load_recordings(conn)
            self.assertEqual([item.key for item in recordings], ["uid:uid-one", "path:two.m4a"])

    def test_title_prefers_encrypted_then_custom_then_path(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = create_database(
                directory,
                [
                    (1, "one", "one.qta", "User Title", "internal-label", 3, 1, None),
                    (2, "two", "two.qta", None, "Custom Fallback", 2, 1, None),
                    (3, "three", "Path Fallback.qta", None, None, 1, 1, None),
                ],
            )
            with open_database(db_path) as conn:
                loaded, _ = load_recordings(conn)
            by_pk = {item.pk: item for item in loaded}
            self.assertEqual(by_pk[1].title, "User Title")
            self.assertEqual(by_pk[2].title, "Custom Fallback")
            self.assertEqual(by_pk[3].title, "Path Fallback")

    def test_blob_text_values_are_decoded(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = create_database(
                directory,
                [(1, b"unique", b"recording.qta", "録音".encode(), None, 0, 1, None)],
            )
            with open_database(db_path) as conn:
                loaded, _ = load_recordings(conn)
            self.assertEqual(loaded[0].unique_id, "unique")
            self.assertEqual(loaded[0].rel_path, "recording.qta")
            self.assertEqual(loaded[0].title, "録音")
            self.assertFalse(loaded[0].title.startswith("b'"))

    def test_snapshot_does_not_change_source_and_is_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = create_database(
                directory,
                [(1, "one", "one.qta", "One", None, 0, 1, None)],
            )
            before = set(os.listdir(directory))
            created = []
            real_mkdtemp = tempfile.mkdtemp

            def tracked_mkdtemp(*args, **kwargs):
                path = real_mkdtemp(*args, **kwargs)
                created.append(path)
                return path

            with mock.patch("vmx_core.tempfile.mkdtemp", side_effect=tracked_mkdtemp):
                with open_database(db_path) as conn:
                    loaded, _ = load_recordings(conn)
                    self.assertEqual(len(loaded), 1)
            self.assertEqual(set(os.listdir(directory)), before)
            self.assertTrue(created)
            self.assertTrue(all(not os.path.exists(path) for path in created))

    def test_hot_wal_in_nonwritable_directory_uses_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = create_database(
                directory,
                [(1, "one", "one.qta", "One", None, 0, 1, None)],
            )
            writer = sqlite3.connect(db_path)
            try:
                writer.execute("PRAGMA journal_mode=WAL")
                writer.execute("PRAGMA wal_autocheckpoint=0")
                writer.execute(
                    """
                    INSERT INTO ZCLOUDRECORDING
                        (Z_PK, ZUNIQUEID, ZPATH, ZENCRYPTEDTITLE, ZCUSTOMLABEL,
                         ZDATE, ZDURATION, ZEVICTIONDATE)
                    VALUES (2, 'two', 'two.qta', 'Two', NULL, 1, 1, NULL)
                    """
                )
                writer.commit()
                shm_path = f"{db_path}-shm"
                if os.path.exists(shm_path):
                    os.unlink(shm_path)
                before = set(os.listdir(directory))
                os.chmod(directory, 0o500)
                try:
                    with open_database(db_path) as conn:
                        loaded, _ = load_recordings(conn)
                    diagnosis = diagnose_database(db_path)
                finally:
                    os.chmod(directory, 0o700)
                self.assertEqual(len(loaded), 2)
                self.assertNotEqual(diagnosis.status, DbStatus.PERMISSION_DENIED)
                self.assertEqual(set(os.listdir(directory)), before)
            finally:
                writer.close()


if __name__ == "__main__":
    unittest.main()
