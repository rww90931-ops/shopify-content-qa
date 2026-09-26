# Shopify Content QA

A small, offline command-line checker for exported Shopify page and blog HTML. It checks whether each page has one H1, a readable title and meta description, descriptive image alt text, and at least one internal link. It also reports internal links whose targets are **not present in the supplied export**. It does not crawl your live store or claim to predict Google rankings.

## Quick start

Requires Python 3.9 or newer; no third-party packages or API keys.

```bash
python -m shopify_content_qa examples --site https://example.com
python -m shopify_content_qa examples --site https://example.com --format json
python -m unittest discover -s tests -v
```

Point the command at a folder of `.html` files exported from your store. A file such as `blogs/news/wig-care.html` is treated as the URL `/blogs/news/wig-care`; `index.html` maps to `/`. This convention enables local cross-link checks. Use `--format json` for CI, and `--fail-on error` to return exit code 1 if any errors are found.

```bash
python -m shopify_content_qa ./export --site https://your-store.example --fail-on error
```

The tool recognizes absolute and relative links on your own domain. It ignores external links, `mailto:`, `tel:`, and fragment-only links. All ordinary internal links are counted, even if marked `nofollow`; this is a structural check, not an endorsement signal. Missing local targets are reported as warnings because an export may be incomplete. If you want to suppress these warnings, use `--no-local-link-check`.

## Checks and limits

| Check | Why it helps |
| --- | --- |
| Missing or multiple H1s | Catches common template/content mistakes. |
| Missing/short/long title and meta description | Prompts a human review; length ranges are heuristics, not Google limits. |
| Images missing meaningful alt text | Improves accessibility and image context. Decorative images with empty alt are allowed when `role="presentation"` or `aria-hidden="true"`. |
| Pages without internal links | Flags isolation; an intentional landing page may be fine. |
| Local links absent from the export | Helps catch typos, but incomplete exports create false positives. |

This is a quality-assurance tool, not an SEO score. It cannot judge whether a page satisfies search intent, whether a claim is accurate, whether a link feels natural, or whether Google indexed a page. Those require editorial review and live data.

## Open source and origin

MIT licensed. Created from the generic, non-proprietary QA checks used by [EWIGSC](https://e-wigs-c.com/) while publishing educational wig content. No private store data or internal editorial files are included.

