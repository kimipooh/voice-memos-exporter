import re
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
IGNORED_SCHEMES = ("http://", "https://", "mailto:")


def slugify_heading(heading):
    lowered = heading.casefold()
    return "".join(
        "-" if character.isspace() else character
        for character in lowered
        if character.isalnum() or character == "-" or character.isspace()
    )


class DocumentationLinkTests(unittest.TestCase):
    def tracked_markdown_files(self):
        try:
            result = subprocess.run(
                ["git", "ls-files", "-z", "--", "*.md"],
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

        return [
            REPO_ROOT / raw_name.decode("utf-8", errors="surrogateescape")
            for raw_name in result.stdout.split(b"\0")
            if raw_name
        ]

    def test_relative_markdown_links_resolve(self):
        for source in self.tracked_markdown_files():
            text = source.read_text(encoding="utf-8")
            for match in MARKDOWN_LINK_RE.finditer(text):
                target = match.group(1).strip()
                if target.startswith(IGNORED_SCHEMES) or target.startswith("#"):
                    continue

                relative_target, separator, anchor = target.partition("#")
                destination = (source.parent / relative_target).resolve()
                source_name = source.relative_to(REPO_ROOT)
                self.assertTrue(
                    destination.exists(),
                    f"{source_name}: broken Markdown target {target!r}",
                )

                if not separator or destination.suffix.casefold() != ".md":
                    continue
                destination_text = destination.read_text(encoding="utf-8")
                headings = [
                    heading_match.group(1)
                    for line in destination_text.splitlines()
                    if (heading_match := HEADING_RE.match(line))
                ]
                if not headings:
                    continue
                slugs = {slugify_heading(heading) for heading in headings}
                self.assertIn(
                    anchor.casefold(),
                    slugs,
                    f"{source_name}: broken Markdown anchor {target!r}",
                )

    def test_tracked_markdown_files_have_no_utf8_bom(self):
        for path in self.tracked_markdown_files():
            relative = path.relative_to(REPO_ROOT)
            self.assertFalse(
                path.read_bytes().startswith(b"\xef\xbb\xbf"),
                f"{relative}: Markdown file has a UTF-8 BOM",
            )


if __name__ == "__main__":
    unittest.main()
