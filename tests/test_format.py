import unittest

from vmx_core import format_duration


class FormatDurationTests(unittest.TestCase):
    def test_unknown_duration(self):
        self.assertEqual(format_duration(None), "-")

    def test_duration_boundaries(self):
        cases = (
            (0, "0:00"),
            (9, "0:09"),
            (65, "1:05"),
            (3599, "59:59"),
            (3600, "1:00:00"),
            (3725, "1:02:05"),
            (-5, "0:00"),
            (65.9, "1:05"),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(format_duration(value), expected)


if __name__ == "__main__":
    unittest.main()
