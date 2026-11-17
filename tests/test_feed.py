"""Run with: python -m unittest discover tests"""
import gzip
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_feed as ff  # noqa: E402

CFG = json.loads((ROOT / "config.json").read_text())
RETAILER = {"id": "test", "name": "Test Retailer"}
RAW = (ROOT / "tests" / "fixture_feed.csv").read_bytes()


def kept(rows):
    return [p for p in (ff.normalise_row(r, RETAILER, CFG) for r in rows) if p]


class FeedTests(unittest.TestCase):
    def test_parses_plain_and_gzip(self):
        self.assertEqual(len(ff.parse_feed(RAW)), 8)
        self.assertEqual(len(ff.parse_feed(gzip.compress(RAW))), 8)

    def test_only_valid_in_range_watches_survive(self):
        products = kept(ff.parse_feed(RAW))
        self.assertEqual([p["id"] for p in products], ["test-T1", "test-T2"])

    def test_values_are_taken_from_feed_unchanged(self):
        p = kept(ff.parse_feed(RAW))[0]
        self.assertEqual(p["price"], 3500.0)
        self.assertEqual(p["was_price"], 3900.0)
        self.assertTrue(p["in_stock"])
        self.assertTrue(p["link"].startswith("https://www.awin1.com/"))
        self.assertEqual(p["reference"], "TB-1000-A")
        self.assertEqual(p["group"], "ean:5012345678900")

    def test_missing_values_stay_missing(self):
        p = kept(ff.parse_feed(RAW))[1]
        self.assertIsNone(p["was_price"])
        self.assertFalse(p["in_stock"])
        self.assertEqual(p["group"], "ref:testbrand:tb2000b")

    def test_excluded_brands_are_dropped(self):
        rows = ff.parse_feed(RAW)
        retailer = {"id": "test", "name": "Test Retailer", "exclude_brands": ["TestBrand"]}
        self.assertEqual([p for p in (ff.normalise_row(r, retailer, CFG) for r in rows) if p], [])

    def test_price_parser_rejects_non_numbers(self):
        for bad in ("POA", "", None, "0", "-5", "1,2,3x"):
            self.assertIsNone(ff.to_price(bad))
        self.assertEqual(ff.to_price("£2,450.00"), 2450.0)

    def test_stock_unknown_is_none(self):
        self.assertIsNone(ff.to_stock(""))
        self.assertIsNone(ff.to_stock("call us"))

    def test_validation_blocks_small_or_collapsed_feeds(self):
        cfg = CFG["feed"]
        self.assertIsNotNone(ff.validate([{}] * 3, [], cfg))
        self.assertIsNotNone(ff.validate([{}] * 40, [{}] * 100, cfg))
        self.assertIsNone(ff.validate([{}] * 90, [{}] * 100, cfg))

    def test_price_history(self):
        old = [{"id": "a", "price": 5000.0, "first_seen": "2026-01-01"}]
        new = ff.apply_history([{"id": "a", "price": 4500.0}, {"id": "b", "price": 3000.0}], old, "2026-02-01")
        self.assertEqual(new[0]["prev_price"], 5000.0)
        self.assertEqual(new[0]["price_changed"], "2026-02-01")
        self.assertIsNone(new[1]["prev_price"])


if __name__ == "__main__":
    unittest.main()
