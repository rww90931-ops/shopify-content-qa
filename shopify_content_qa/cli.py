"""Inspect a directory of HTML files without making network requests."""

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse


@dataclass
class Finding:
    file: str
    severity: str
    code: str
    message: str


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_parts = []
        self.h1_parts = []
        self.meta_description = ""
        self.images = []
        self.links = []
        self._title = False
        self._h1 = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "title":
            self._title = True
            self.title_parts.append("")
        elif tag == "h1":
            self._h1 = True
            self.h1_parts.append("")
        elif tag == "meta" and (values.get("name") or "").lower() == "description":
            self.meta_description = values.get("content") or ""
        elif tag == "img":
            self.images.append(values)
        elif tag == "a" and values.get("href"):
            self.links.append(values["href"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._title = False
        elif tag == "h1":
            self._h1 = False

    def handle_data(self, data):
        if self._title and self.title_parts:
            self.title_parts[-1] += data
        if self._h1 and self.h1_parts:
            self.h1_parts[-1] += data


def page_path(file, root):
    relative = file.relative_to(root).with_suffix("").as_posix()
    if relative == "index":
        return "/"
    if relative.endswith("/index"):
        relative = relative[:-6]
    return "/" + relative


def normalized_path(value):
    path = unquote(value).rstrip("/") or "/"
    return path.removesuffix(".html") if path != "/" else path


def internal_target(href, base_url, page_url):
    if href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    parsed = urlparse(urljoin(page_url, href))
    home = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or parsed.netloc.lower() != home.netloc.lower():
        return None
    return normalized_path(parsed.path)


def inspect(root, site, check_local_links=True):
    files = sorted(root.rglob("*.html"))
    paths = {normalized_path(page_path(file, root)) for file in files}
    findings = []
    for file in files:
        name = file.relative_to(root).as_posix()
        parser = PageParser()
        try:
            parser.feed(file.read_text(encoding="utf-8"))
            parser.close()
        except (UnicodeError, OSError) as exc:
            findings.append(Finding(name, "error", "read_error", str(exc)))
            continue
        title = " ".join(parser.title_parts).strip()
        description = parser.meta_description.strip()
        h1s = [x.strip() for x in parser.h1_parts]
        if not title:
            findings.append(Finding(name, "error", "missing_title", "No <title> found."))
        elif not 25 <= len(title) <= 70:
            findings.append(Finding(name, "info", "review_title_length", f"Title is {len(title)} characters; review it for clarity."))
        if not description:
            findings.append(Finding(name, "warning", "missing_description", "No meta description found."))
        elif not 70 <= len(description) <= 180:
            findings.append(Finding(name, "info", "review_description_length", f"Meta description is {len(description)} characters; review it for clarity."))
        if len(h1s) != 1 or not h1s[0]:
            findings.append(Finding(name, "warning", "h1_count", f"Expected one non-empty H1; found {len(h1s)}."))
        for index, img in enumerate(parser.images, 1):
            decorative = img.get("role") == "presentation" or img.get("aria-hidden") == "true"
            if not decorative and not (img.get("alt") or "").strip():
                findings.append(Finding(name, "warning", "missing_image_alt", f"Image {index} has no descriptive alt text."))
        base = site.rstrip("/") + "/"
        page_url = urljoin(base, page_path(file, root).lstrip("/"))
        targets = {target for href in parser.links if (target := internal_target(href, base, page_url))}
        if not targets:
            findings.append(Finding(name, "info", "no_internal_links", "No internal links found; review whether this page needs one."))
        if check_local_links:
            for target in sorted(targets - paths):
                findings.append(Finding(name, "warning", "target_not_in_export", f"Internal link target {target} is not in this export."))
    return files, findings


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("directory", type=Path, help="Folder containing .html files")
    cli.add_argument("--site", required=True, help="Canonical site origin, e.g. https://example.com")
    cli.add_argument("--format", choices=("text", "json"), default="text")
    cli.add_argument("--fail-on", choices=("none", "error", "warning"), default="none")
    cli.add_argument("--no-local-link-check", action="store_true")
    args = cli.parse_args(argv)
    if not args.directory.is_dir():
        cli.error("directory must exist")
    parsed = urlparse(args.site)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        cli.error("--site must be an absolute http(s) URL")
    files, findings = inspect(args.directory, args.site, not args.no_local_link_check)
    if not files:
        cli.error("no .html files found")
    if args.format == "json":
        print(json.dumps({"pages": len(files), "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        print(f"Checked {len(files)} page(s); {len(findings)} finding(s).")
        for finding in findings:
            print(f"{finding.file}: {finding.severity}: {finding.code}: {finding.message}")
    if args.fail_on == "error" and any(x.severity == "error" for x in findings):
        return 1
    if args.fail_on == "warning" and any(x.severity in ("error", "warning") for x in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

