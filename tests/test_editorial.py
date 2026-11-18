"""Run with: python -m unittest discover tests"""
import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import editorial  # noqa: E402

TODAY = dt.date(2026, 11, 17)
CAT = {"a": {"id": "a", "price": 2500.0, "in_stock": True},
       "b": {"id": "b", "price": 3500.0, "in_stock": True},
       "c": {"id": "c", "price": 2000.0, "in_stock": False}}


def art(**kw):
    base = {"_file": "x.md", "_body": "Text.", "title": "T", "slug": "t", "type": "guide", "status": "published",
            "description": "D", "published": TODAY, "basis": "Researched.", "products": ["a"]}
    base.update(kw)
    return base


def levels(a):
    return [lvl for lvl, _ in editorial.check_article(a, CAT, TODAY)]


class EditorialTests(unittest.TestCase):
    def test_clean_article_passes(self):
        self.assertEqual(editorial.check_article(art(), CAT, TODAY), [])

    def test_missing_product_is_flagged(self):
        self.assertIn("flag", levels(art(products=["gone"])))

    def test_out_of_stock_is_flagged(self):
        self.assertIn("flag", levels(art(products=["c"])))

    def test_price_above_ceiling_is_flagged(self):
        self.assertIn("flag", levels(art(products=["b"], price_ceiling=3000)))
        self.assertEqual(levels(art(products=["a"], price_ceiling=3000)), [])

    def test_inline_product_tokens_are_checked(self):
        self.assertIn("flag", levels(art(products=[], _body="See {{product:gone}}")))

    def test_drafts_and_future_posts_are_not_live(self):
        self.assertFalse(editorial.is_live(art(status="draft"), TODAY))
        self.assertFalse(editorial.is_live(art(status="approved"), TODAY))
        self.assertFalse(editorial.is_live(art(publish_after=TODAY + dt.timedelta(days=1)), TODAY))
        self.assertTrue(editorial.is_live(art(), TODAY))

    def test_watch_of_the_week_needs_one_product(self):
        self.assertIn("error", levels(art(type="watch-of-the-week", products=["a", "b"])))

    def test_news_needs_sources_with_https(self):
        self.assertIn("error", levels(art(type="news")))
        self.assertIn("error", levels(art(type="news", sources=[{"title": "S", "url": "http://x"}])))

    def test_hands_on_wording_is_flagged(self):
        self.assertIn("flag", levels(art(_body="We tested it for a week.")))

    def test_bad_slug_is_an_error(self):
        self.assertIn("error", levels(art(slug="Bad Slug")))


if __name__ == "__main__":
    unittest.main()


# --- submissions -------------------------------------------------------------
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from validate_submission import extract_article, validate  # noqa: E402

SUB = """---
title: "Watch of the Week: Test"
slug: wotw-test
type: watch-of-the-week
status: review
published: 2026-11-23
description: "d"
basis: "Researched."
products: [p1]
image_credit: "feed"
---
Body {{product:p1}}
"""


def test_extract_from_issue_form():
    body = "### Type\n\nwatch-of-the-week\n\n### Article file\n\n```markdown\n" + SUB + "```\n\n### Verification notes\n\nx"
    assert extract_article(body).startswith("---\ntitle:")


def test_extract_bare_paste():
    assert "slug: wotw-test" in extract_article("Here it is:\n" + SUB + "\n### Verification notes\nx")


def test_clean_submission_has_no_errors():
    _, issues = validate(SUB, {"p1": {"brand": "B", "name": "N", "price": 100, "in_stock": True}}, dt.date(2026, 11, 20))
    assert not [m for lvl, m in issues if lvl == "error"]


def test_submission_rejects_raw_links_long_quotes_and_published():
    bad = SUB.replace("status: review", "status: approved").replace(
        "Body", 'Body https://www.awin1.com/x "' + " ".join(["word"] * 20) + '"')
    _, issues = validate(bad, {"p1": {"brand": "B", "name": "N", "price": 100, "in_stock": True}}, dt.date(2026, 11, 20))
    errs = " ".join(m for lvl, m in issues if lvl == "error")
    assert "raw retailer" in errs and "quotation" in errs and "status: review" in errs


def test_unknown_product_and_bad_yaml():
    _, issues = validate(SUB, {}, dt.date(2026, 11, 20))
    assert any("no longer in the catalogue" in m for _, m in issues)
    a, issues = validate("---\ntitle: [unclosed\n---\nx", {}, dt.date(2026, 11, 20))
    assert issues and issues[0][0] == "error"


def test_grok_cannot_self_approve():
    for st in ("approved", "published", "draft"):
        _, issues = validate(SUB.replace("status: review", "status: " + st),
                             {"p1": {"brand": "B", "name": "N", "price": 100, "in_stock": True}}, dt.date(2026, 11, 20))
        assert any("status: review" in m for lvl, m in issues if lvl == "error"), st


# --- no automated affiliate clicks ---------------------------------------------
def test_link_checker_never_requests_links():
    src = (Path(__file__).resolve().parent.parent / "scripts" / "check_affiliate_links.py").read_text()
    assert "urllib.request" not in src and "urlopen" not in src and "requests" not in src


def test_grok_is_told_not_to_click_affiliate_links():
    root = Path(__file__).resolve().parent.parent
    assert "Never open or follow" in (root / "ops" / "GROK_SYSTEM_PROMPT.md").read_text()
    assert "Never open or follow any affiliate link" in (root / "scripts" / "grok_writer.py").read_text()
