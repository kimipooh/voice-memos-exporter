import unittest

from vmx_core import safe_filename


class SafeFilenameTests(unittest.TestCase):
    def test_slash_is_replaced(self):
        name = safe_filename("Interview / Hanoi", ".m4a", fallback="fallback")
        self.assertEqual(name, "Interview - Hanoi.m4a")
        self.assertNotIn("/", name)

    def test_empty_dot_dotdot_and_whitespace_use_fallback(self):
        for title in ("", ".", "..", "   "):
            with self.subTest(title=title):
                self.assertEqual(safe_filename(title, ".m4a", fallback="original"), "original.m4a")

    def test_leading_dot_is_not_hidden(self):
        self.assertEqual(safe_filename(".private", ".m4a", fallback="original"), "private.m4a")

    def test_control_characters_are_removed(self):
        name = safe_filename("nul\x00line\nend\x7f", ".m4a", fallback="original")
        self.assertEqual(name, "nullineend.m4a")

    def test_long_multibyte_name_is_valid_and_bounded(self):
        name = safe_filename("会" * 300, ".m4a", fallback="original")
        self.assertLessEqual(len(name.encode("utf-8")), 255)
        name.encode("utf-8").decode("utf-8")

    def test_unicode_is_preserved(self):
        for title in ("日本語", "Phỏng vấn", "บันทึก", "🎙️✨"):
            with self.subTest(title=title):
                self.assertEqual(safe_filename(title, ".m4a", fallback="x"), title + ".m4a")

    def test_numeric_string_and_int_do_not_fail(self):
        self.assertEqual(safe_filename("20240910", ".m4a", fallback="x"), "20240910.m4a")
        self.assertEqual(safe_filename(20240910, ".m4a", fallback="x"), "20240910.m4a")


if __name__ == "__main__":
    unittest.main()
