import os
import tempfile
import unittest

from data_zestimate import scan_dir, value_corpus
from data_zestimate.core import freshness_factor, uniqueness_factor


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = self.tmp.name
        with open(os.path.join(d, "a.txt"), "w") as f:
            f.write("hello world this is line one\n" * 10)
        with open(os.path.join(d, "b.md"), "w") as f:
            f.write("a completely different line of text\nanother distinct line here\n")
        with open(os.path.join(d, "img.png"), "wb") as f:
            f.write(b"\x89PNG")

    def tearDown(self):
        self.tmp.cleanup()

    def test_profile_counts_text_only_and_dedupes(self):
        p = scan_dir(self.tmp.name)
        self.assertEqual(p.files, 2)
        self.assertGreater(p.tokens, p.unique_tokens)
        self.assertLess(p.unique_ratio, 0.5)

    def test_value_monotonic_in_license_and_exclusivity(self):
        p = scan_dir(self.tmp.name)
        unclear = value_corpus(p, "legal", "unclear").mid
        clear = value_corpus(p, "legal", "clear").mid
        excl = value_corpus(p, "legal", "clear", exclusive=True).mid
        self.assertLess(unclear, clear)
        self.assertAlmostEqual(excl / clear, 2.5)

    def test_range_brackets_mid(self):
        v = value_corpus(scan_dir(self.tmp.name), "medical", "clear")
        self.assertLess(v.low, v.mid)
        self.assertLess(v.mid, v.high)

    def test_unknown_domain_rejected(self):
        with self.assertRaises(ValueError):
            value_corpus(scan_dir(self.tmp.name), "astrology")

    def test_spread_that_would_make_the_low_estimate_negative_is_rejected(self):
        for spread in (1.0, 1.5, -0.1):
            with self.subTest(spread=spread), self.assertRaises(ValueError):
                value_corpus(scan_dir(self.tmp.name), "medical", "clear", spread=spread)


class FactorTests(unittest.TestCase):
    def test_factors(self):
        self.assertEqual(freshness_factor(6), 1.0)
        self.assertEqual(freshness_factor(200), 0.5)
        self.assertAlmostEqual(uniqueness_factor(1.0), 1.2)
        self.assertEqual(uniqueness_factor(0.0), 0.2)


if __name__ == "__main__":
    unittest.main()
