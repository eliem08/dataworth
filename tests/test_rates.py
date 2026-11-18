"""Rate cards: built from comparable deals or written by hand, and used by scan and domains."""

import contextlib
import io
import json
import pathlib
import statistics
import tempfile
import unittest

from dataworth.__main__ import main
from dataworth.core import CorpusProfile, value_corpus
from dataworth.rates import RateCard, load_rates, rates_from_deals

EX = pathlib.Path(__file__).resolve().parent.parent / "examples"


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


class RateCardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def csv(self, text):
        p = self.dir / "deals.csv"
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_rates_back_out_licence_exclusivity_and_age(self):
        card = rates_from_deals(
            self.csv(
                "domain,mtokens,price_usd,license,exclusive,age_months\n"
                "legal,100,1000,clear,no,0\n"  # 10.00 / M
                "legal,100,600,mixed,no,0\n"  # 600 / (100 x 0.6) = 10.00
                "legal,100,5000,clear,yes,0\n"  # 5000 / (100 x 2.5) = 20.00
            )
        )
        self.assertEqual(card.domains["legal"], 10.0)  # median
        self.assertEqual(card.deals, {"legal": 3})
        self.assertEqual(card.domains["medical"], 25.0)  # domains with no deals keep the built-in rate
        aged = rates_from_deals(self.csv("domain,mtokens,price_usd,age_months\ncode,10,70,22\n"))
        self.assertAlmostEqual(aged.domains["code"], 70 / 10 / 0.7, places=3)  # 22 months old: freshness 0.7

    def test_spread_follows_how_much_deals_disagree(self):
        tight = rates_from_deals(self.csv("domain,mtokens,price_usd\n" + "x,1,10\nx,1,10.5\nx,1,9.5\nx,1,10\n"))
        loose = rates_from_deals(self.csv("domain,mtokens,price_usd\n" + "x,1,2\nx,1,10\nx,1,30\nx,1,60\n"))
        self.assertEqual(tight.spread, 0.1)  # floor
        self.assertGreater(loose.spread, 0.5)
        one = rates_from_deals(self.csv("domain,mtokens,price_usd\nx,1,10\n"))
        self.assertEqual(one.spread, 0.35)  # too few deals to measure: default

    def test_bad_deal_rows_name_the_line(self):
        for body, msg in (
            ("legal,0,100", "line 2"),
            ("legal,10,-5", "price_usd"),
            (",10,5", "domain is empty"),
            ("legal,10,abc", "price_usd"),
        ):
            with self.assertRaisesRegex(ValueError, msg):
                rates_from_deals(self.csv("domain,mtokens,price_usd\n" + body + "\n"))
        with self.assertRaisesRegex(ValueError, "license"):
            rates_from_deals(self.csv("domain,mtokens,price_usd,license\nx,1,1,stolen\n"))
        with self.assertRaisesRegex(ValueError, "no deals"):
            rates_from_deals(self.csv("domain,mtokens,price_usd\n"))

    def test_hand_written_card_and_validation(self):
        p = self.dir / "card.json"
        p.write_text(json.dumps({"domains": {"legal": 40}, "exclusive_multiplier": 3, "spread": 0.2}), encoding="utf-8")
        card = load_rates(str(p))
        prof = CorpusProfile(path=".", files=1, bytes=1, tokens=2_000_000, unique_tokens=2_000_000)
        val = value_corpus(prof, "legal", "clear", 0, True, rates=card)
        self.assertEqual(val.factors["base_rate"], 40)
        self.assertEqual(val.factors["exclusivity"], 3)
        self.assertAlmostEqual(val.low, val.mid * 0.8)
        for bad in ({"domains": {"x": -1}}, {"spread": 2}, {"license": {"clear": 1.5}}, {"exclusive_multiplier": 0.5}):
            p.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_rates(str(p))
        self.assertEqual(RateCard().source, "built-in estimates")

    def test_cli_round_trip_with_the_example_deals(self):
        card = str(self.dir / "card.json")
        code, out = run("rates-from-deals", str(EX / "deals.csv"), "--out", card)
        self.assertEqual(code, 0, out)
        self.assertIn("forum", out)
        _, out = run("domains", "--rates", card)
        self.assertIn("(3 deals)", out)
        corpus = self.dir / "corpus"
        corpus.mkdir()
        (corpus / "a.txt").write_text(
            "contract clause " * 4000 + " ".join(str(i) for i in range(3000)), encoding="utf-8"
        )
        code, out = run("scan", str(corpus), "--domain", "forum", "--license", "clear", "--rates", card)
        self.assertEqual(code, 0, out)
        self.assertIn("1 deals", out)
        self.assertEqual(run("scan", str(corpus), "--domain", "forum")[0], 2)  # not a built-in domain
        rates = json.loads(pathlib.Path(card).read_text(encoding="utf-8"))
        # 9000/400; 4500/(250 x 0.6 x freshness 0.82 at 18 months); 52000/(900 x 2.5 exclusive)
        expected = statistics.median([9000 / 400, 4500 / (250 * 0.6 * 0.82), 52000 / (900 * 2.5)])
        self.assertAlmostEqual(rates["domains"]["legal"], expected, places=3)


if __name__ == "__main__":
    unittest.main()
