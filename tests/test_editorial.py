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
