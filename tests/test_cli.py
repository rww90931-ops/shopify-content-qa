import tempfile
import unittest
from pathlib import Path

from shopify_content_qa.cli import inspect, internal_target, main, page_path


class ContentQATests(unittest.TestCase):
    def test_paths_and_internal_links(self):
        root = Path("export")
        self.assertEqual(page_path(root / "index.html", root), "/")
        self.assertEqual(page_path(root / "blogs" / "news" / "guide.html", root), "/blogs/news/guide")
        self.assertEqual(internal_target("/blogs/news/guide?x=1", "https://example.com/", "https://example.com/"), "/blogs/news/guide")
        self.assertIsNone(internal_target("https://other.com/page", "https://example.com/", "https://example.com/"))

    def test_finds_missing_metadata_and_alt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text('<html><body><img src="a.jpg"><h1>A</h1><h1>B</h1></body></html>', encoding="utf-8")
            files, findings = inspect(root, "https://example.com")
            self.assertEqual(len(files), 1)
            codes = {finding.code for finding in findings}
            self.assertTrue({"missing_title", "missing_description", "h1_count", "missing_image_alt", "no_internal_links"} <= codes)

    def test_local_target_check_and_suppression(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "index.html").write_text('<title>A sufficiently long example page title</title><meta name="description" content="A sufficiently long example meta description for this page, with enough plain language to explain what it contains."><h1>Home</h1><a href="/missing">Read more</a>', encoding="utf-8")
            _, findings = inspect(root, "https://example.com")
            self.assertIn("target_not_in_export", {finding.code for finding in findings})
            _, findings = inspect(root, "https://example.com", False)
            self.assertNotIn("target_not_in_export", {finding.code for finding in findings})

    def test_examples_clean(self):
        root = Path(__file__).resolve().parents[1] / "examples"
        files, findings = inspect(root, "https://example.com")
        self.assertEqual(len(files), 2)
        self.assertEqual([f for f in findings if f.severity in ("error", "warning")], [])


if __name__ == "__main__":
    unittest.main()

