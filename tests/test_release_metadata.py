import subprocess
import unittest
from pathlib import Path

import vmx_core

try:
    import voice_memos_exporter
except (ImportError, ModuleNotFoundError):
    voice_memos_exporter = None


REPO_ROOT = Path(__file__).resolve().parents[1]
UNRESOLVED_LICENSE_PHRASES = (
    "local-only",
    "local use only",
    "for local use",
    "not for redistribution",
    "do not distribute",
    "do not redistribute",
    "do not publish",
    "license status is unresolved",
    "license status remains unresolved",
    "license is unresolved",
    "license is currently unclear",
    "licensing terms are currently unclear",
    "no clear license",
    "clear license file",
    "not offered as a release",
    "no release or binary distribution",
    "ローカル専用",
    "再配布しないで",
    "ライセンスは現在不明確",
    "ライセンスが未解決",
)


class ReleaseMetadataTests(unittest.TestCase):
    def test_license_file_is_mit_with_both_copyrights(self):
        license_path = REPO_ROOT / "LICENSE"
        self.assertTrue(license_path.exists())
        raw = license_path.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        text = raw.decode("utf-8")
        self.assertTrue(text.startswith("MIT License"))
        upstream = "Copyright (c) 2026 rudrakabir"
        fork = "Copyright (c) 2026 Kimiya Kitani"
        self.assertIn(upstream, text)
        self.assertIn(fork, text)
        self.assertLess(text.index(upstream), text.index(fork))
        self.assertIn("Permission is hereby granted, free of charge", text)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', text)

    def test_notice_records_both_parties_and_mit(self):
        text = (REPO_ROOT / "NOTICE").read_text(encoding="utf-8")
        self.assertIn("rudrakabir", text)
        self.assertIn("Kimiya Kitani", text)
        self.assertIn("MIT License", text)
        lowered = text.casefold()
        for phrase in UNRESOLVED_LICENSE_PHRASES:
            self.assertNotIn(phrase.casefold(), lowered)

    def test_version_is_consistent_across_sources(self):
        self.assertEqual(vmx_core.TOOL_VERSION, "1.1.0")
        if voice_memos_exporter is not None:
            self.assertEqual(
                voice_memos_exporter.APP_VERSION, vmx_core.TOOL_VERSION
            )
        spec = (REPO_ROOT / "packaging" / "voice_memos_exporter.spec").read_text(
            encoding="utf-8"
        )
        self.assertIn('"CFBundleShortVersionString": "1.1.0"', spec)
        self.assertIn('"CFBundleVersion": "1.1.0"', spec)
        changelog = (REPO_ROOT / "docs" / "CHANGELOG.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## [1.1.0]", changelog)

    def test_bundle_identifier_has_no_local_suffix(self):
        spec = (REPO_ROOT / "packaging" / "voice_memos_exporter.spec").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            'bundle_identifier="jp.kitani.voicememosexporter"', spec
        )
        self.assertNotIn("jp.kitani.voicememosexporter" + ".local", spec)

    def test_tracked_files_have_no_local_only_or_unresolved_license_wording(self):
        try:
            result = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
            )
        except OSError as exc:
            self.skipTest(f"git unavailable: {exc}")
        if result.returncode != 0:
            self.skipTest(
                f"git ls-files failed with exit status {result.returncode}"
            )

        for raw_name in result.stdout.split(b"\0"):
            if not raw_name:
                continue
            relative = raw_name.decode("utf-8", errors="surrogateescape")
            if relative == "tests/test_release_metadata.py":
                continue
            path = REPO_ROOT / relative
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            lowered = text.casefold()
            for phrase in UNRESOLVED_LICENSE_PHRASES:
                self.assertNotIn(
                    phrase.casefold(),
                    lowered,
                    f"offending file {relative!r} contains phrase {phrase!r}",
                )

    def test_readmes_document_gui_and_cli_and_mit(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        for expected in (
            "Quick Start (GUI app)",
            "Quick Start (CLI)",
            "MIT License",
            "rudrakabir",
            "Kimiya Kitani",
            "1.1.0",
        ):
            self.assertIn(expected, readme)

        readme_ja = (REPO_ROOT / "README-ja.md").read_text(encoding="utf-8")
        for expected in (
            "クイックスタート（GUIアプリ）",
            "クイックスタート（CLI）",
            "MIT License",
            "rudrakabir",
            "Kimiya Kitani",
            "1.1.0",
        ):
            self.assertIn(expected, readme_ja)


if __name__ == "__main__":
    unittest.main()
