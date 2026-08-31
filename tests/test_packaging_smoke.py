import json
import os
import plistlib
import shutil
import subprocess
import unittest
from pathlib import Path

from voice_memos_exporter import APP_COPYRIGHT, full_disk_access_steps


REPO_ROOT = Path(__file__).resolve().parents[1]
APP = REPO_ROOT / "dist" / "Voice Memos Exporter.app"
EXECUTABLE = APP / "Contents" / "MacOS" / "Voice Memos Exporter"
INFO_PLIST = APP / "Contents" / "Info.plist"
FRAMEWORKS = APP / "Contents" / "Frameworks"


class FullDiskAccessStepsTests(unittest.TestCase):
    def test_packaged_and_script_guidance(self):
        packaged = "\n".join(full_disk_access_steps(True))
        script = "\n".join(full_disk_access_steps(False))

        self.assertIn("Voice Memos Exporter.app", packaged)
        self.assertNotIn("terminal application", packaged.lower())
        self.assertIn("terminal application", script.lower())


class PackagingMetadataTests(unittest.TestCase):
    def test_spec_contains_attribution_identifier_and_version(self):
        spec = (REPO_ROOT / "packaging" / "voice_memos_exporter.spec").read_text(
            encoding="utf-8"
        )

        self.assertIn(APP_COPYRIGHT, spec)
        self.assertIn("jp.kitani.voicememosexporter", spec)
        self.assertNotIn("jp.kitani.voicememosexporter" + ".local", spec)
        self.assertIn("1.1.0", spec)


@unittest.skipUnless(APP.exists(), "packaged .app not built")
class PackagingSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = os.environ.copy()
        env["VMX_APP_SELFTEST"] = "1"
        cls.selftest = subprocess.run(
            [str(EXECUTABLE)],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )

    def test_bundle_layout_and_identifier(self):
        self.assertTrue(APP.is_dir())
        self.assertTrue(EXECUTABLE.is_file())
        self.assertTrue(os.access(str(EXECUTABLE), os.X_OK))
        self.assertTrue(INFO_PLIST.is_file())
        with INFO_PLIST.open("rb") as handle:
            info = plistlib.load(handle)
        self.assertEqual(info["CFBundleIdentifier"], "jp.kitani.voicememosexporter")
        self.assertEqual(info["NSHumanReadableCopyright"], APP_COPYRIGHT)
        self.assertEqual(info["CFBundleShortVersionString"], "1.1.0")
        self.assertEqual(info["CFBundleVersion"], "1.1.0")

    def test_bundled_tcl_tk_libraries_exist(self):
        self.assertTrue(list(FRAMEWORKS.glob("libtcl9*.dylib")))
        self.assertTrue(list(FRAMEWORKS.glob("libtcl9tk9*.dylib")))

    def test_selftest(self):
        self.assertEqual(self.selftest.returncode, 0, self.selftest.stderr)
        payload = json.loads(self.selftest.stdout)
        self.assertIs(payload["frozen"], True)
        self.assertIs(payload["vmx_core_ok"], True)
        self.assertTrue(payload["tk_version"].startswith("9."))

    def test_bundle_independence(self):
        self.assertEqual(self.selftest.returncode, 0, self.selftest.stderr)
        payload = json.loads(self.selftest.stdout)
        app_root = str(APP.resolve())
        self.assertEqual(os.path.commonpath([app_root, payload["executable"]]), app_root)
        self.assertEqual(os.path.commonpath([app_root, payload["prefix"]]), app_root)

        otool = shutil.which("otool")
        if otool is None:
            self.skipTest("otool unavailable")
        result = subprocess.run(
            [otool, "-L", str(EXECUTABLE)],
            check=True,
            capture_output=True,
            text=True,
        )
        lowered = result.stdout.lower()
        self.assertNotIn("/opt/homebrew", lowered)
        self.assertNotIn("/library/frameworks/python.framework", lowered)
        self.assertNotIn("/usr/bin/python3", lowered)


if __name__ == "__main__":
    unittest.main()
