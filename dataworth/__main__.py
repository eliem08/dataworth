import argparse
import csv
import json
import math
import os
import sys

from .core import scan_dir, value_corpus
from .rates import RateCard, load_rates, rates_from_deals


def _finite_float(s: str) -> float:
    """argparse type: a float that is not nan/inf, so limits and prices cannot be bypassed."""
    v = float(s)
    if not math.isfinite(v):
        raise argparse.ArgumentTypeError(f"must be a finite number, got {s!r}")
    return v


def build_parser():
    ap = argparse.ArgumentParser(prog="dataworth", description="Estimate what a data corpus is worth to an AI lab.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="scan a directory and value it")
    s.add_argument("path")
    s.add_argument("--domain", default="general", help="see `dataworth domains`")
    s.add_argument("--license", default="mixed", help="clear, mixed or unclear (or your rate card's own)")
    s.add_argument("--rates", help="your rate card JSON (from rates-from-deals or written by hand)")
    s.add_argument("--age-months", type=_finite_float, default=0)
    s.add_argument("--exclusive", action="store_true")
    s.add_argument("--json", action="store_true")
    sub.add_parser("domains", help="list domain base rates").add_argument("--rates", help="your rate card JSON")
    d = sub.add_parser("rates-from-deals", help="build a rate card from comparable data deals (CSV)")
    d.add_argument("deals", help="CSV: domain, unique_tokens or mtokens, price_usd[, license, exclusive, age_months]")
    d.add_argument("--out", help="write the rate card here (default: print it)")
    return ap


def _run(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)

    if a.cmd == "rates-from-deals":
        card = rates_from_deals(a.deals)
        text = json.dumps(card.to_dict(), indent=2)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
            print(f"rate card from {card.source} written to {a.out}")
            for d, n in sorted(card.deals.items()):
                print(f"  {d:<15} ${card.domains[d]:>8.2f} / M unique tokens  ({n} deal{'s' * (n != 1)})")
            print(f"  spread +/-{card.spread:.0%}")
        else:
            print(text)
        return 0
    card = load_rates(a.rates) if getattr(a, "rates", None) else RateCard()
    if a.cmd == "domains":
        print(f"rates: {card.source}")
        for d, r in sorted(card.domains.items(), key=lambda kv: kv[1]):
            basis = f"  ({card.deals[d]} deals)" if d in card.deals else ""
            print(f"{d:<15} ${r:>6.2f} / M unique tokens{basis}")
        return 0

    prof = scan_dir(a.path)
    if not prof.files:
        print("no text files found", file=sys.stderr)
        return 1
    val = value_corpus(prof, a.domain, a.license, a.age_months, a.exclusive, rates=card)
    if a.json:
        print(
            json.dumps(
                {"profile": {**prof.__dict__, "unique_ratio": prof.unique_ratio}, "valuation": val.to_dict()}, indent=2
            )
        )
        return 0
    print(f"Corpus:          {prof.path}")
    print(f"Files:           {prof.files:,}   Size: {prof.bytes / 1e6:.1f} MB")
    print(f"Est. tokens:     {prof.tokens:,}  (unique {prof.unique_ratio:.1%})")
    basis = f"{card.deals[a.domain]} deals" if a.domain in card.deals else card.source
    print(f"Domain:          {a.domain}  (${val.factors['base_rate']:.2f} / M unique tokens; {basis})")
    for k, v in val.factors.items():
        print(f"  {k:<14} {v:g}")
    print(f"Estimate:        ${val.mid:,.0f}  (range ${val.low:,.0f} - ${val.high:,.0f})")
    return 0


def main(argv=None):
    """Run the CLI; a bad input file or argument exits 2 with a one-line error instead of a traceback.

    Set AGENT_ECONOMY_DEBUG=1 to see the full traceback.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        return _run(argv)
    except (OSError, ValueError, KeyError, csv.Error) as e:
        if os.environ.get("AGENT_ECONOMY_DEBUG"):
            raise
        msg = e.args[0] if isinstance(e, KeyError) and e.args else e
        print(f"error: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
