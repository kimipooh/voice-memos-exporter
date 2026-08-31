import os
import plistlib
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SCRIPT = REPO_ROOT / "packaging" / "package_app.sh"
REQUIRED_COMMANDS = ("ditto", "/usr/libexec/PlistBuddy", "/usr/bin/plutil", "/usr/bin/unzip")


@unittest.skipUnless(
    all(Path(command).exists() if command.startswith("/") else shutil.which(command) for command in REQUIRED_COMMANDS),
    "macOS packaging commands unavailable",
)
class PackageScriptTests(unittest.TestCase):
    def make_fixture_app(self, root, selftest_valid=True):
        app = root / "dist" / "Voice Memos Exporter.app"
        executable = app / "Contents" / "MacOS" / "Voice Memos Exporter"
        frameworks = app / "Contents" / "Frameworks"
        resources = app / "Contents" / "Resources"
        executable.parent.mkdir(parents=True)
        frameworks.mkdir()
        resources.mkdir()
        with (app / "Contents" / "Info.plist").open("wb") as handle:
            plistlib.dump(
                {
                    "CFBundleIdentifier": "jp.kitani.voicememosexporter",
                    "CFBundleShortVersionString": "9.9.9",
                    "CFBundleVersion": "9.9.9",
                },
                handle,
            )
        selftest_payload = "{'frozen': True, 'vmx_core_ok': True}"
        if not selftest_valid:
            selftest_payload = "{'frozen': False, 'vmx_core_ok': True}"
        executable.write_text(
            "#!/usr/bin/env python3\n"
            "import json\n"
            f"print(json.dumps({selftest_payload}))\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        (frameworks / "target.dylib").write_text("fixture", encoding="utf-8")
        (frameworks / "linked.dylib").symlink_to("target.dylib")
        return app

    def run_script(self, root):
        return subprocess.run(
            ["bash", "packaging/package_app.sh"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_packages_fixture_and_removes_app_only_after_verification(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            packaging = root / "packaging"
            packaging.mkdir()
            shutil.copy2(PACKAGE_SCRIPT, packaging / "package_app.sh")
            app = self.make_fixture_app(root)

            result = self.run_script(root)

            archive = root / "dist" / "Voice-Memos-Exporter-v9.9.9-macOS-arm64.zip"
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(archive.is_file())
            self.assertFalse(app.exists())

    def test_existing_archive_is_not_overwritten_and_keeps_app(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            packaging = root / "packaging"
            packaging.mkdir()
            shutil.copy2(PACKAGE_SCRIPT, packaging / "package_app.sh")
            app = self.make_fixture_app(root)
            archive = root / "dist" / "Voice-Memos-Exporter-v9.9.9-macOS-arm64.zip"
            archive.write_bytes(b"existing archive")

            result = self.run_script(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("refusing to overwrite existing ZIP", result.stderr)
            self.assertIn("size=16 bytes", result.stderr)
            self.assertTrue(app.is_dir())
            self.assertEqual(archive.read_bytes(), b"existing archive")

    def test_failed_verification_keeps_app_and_new_archive(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            packaging = root / "packaging"
            packaging.mkdir()
            shutil.copy2(PACKAGE_SCRIPT, packaging / "package_app.sh")
            app = self.make_fixture_app(root, selftest_valid=False)

            result = self.run_script(root)

            archive = root / "dist" / "Voice-Memos-Exporter-v9.9.9-macOS-arm64.zip"
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bundled selftest failed", result.stderr)
            self.assertTrue(app.is_dir())
            self.assertTrue(archive.is_file())


if __name__ == "__main__":
    unittest.main()
