"""Rate cards: replace the built-in market guesses with your own numbers or with rates derived from real deals.

A rate card is JSON:
  {"domains": {"legal": 15.0, ...},          USD per million unique tokens
   "license": {"clear": 1.0, "mixed": 0.6, "unclear": 0.25},
   "exclusive_multiplier": 2.5,
   "spread": 0.35}                           low/high band around the estimate (0 to 0.9)
Any key left out keeps the built-in value.

`rates_from_deals` reads comparable deals (CSV columns: domain, unique_tokens or mtokens, price_usd, and optional
license, exclusive, age_months) and backs out the rate each deal implies after the licence, exclusivity and age
factors. The domain rate is the median across its deals; with three or more deals overall, the spread comes from
how far they disagree (interquartile range over the median).
"""

from __future__ import annotations

import csv
import json
import math
import statistics
from dataclasses import dataclass, field

from .core import DOMAIN_RATES, LICENSE_FACTORS, freshness_factor

DEFAULT_EXCLUSIVE = 2.5
DEFAULT_SPREAD = 0.35
TRUE = {"1", "true", "yes", "y", "exclusive"}


@dataclass
class RateCard:
    domains: dict = field(default_factory=lambda: dict(DOMAIN_RATES))
    license: dict = field(default_factory=lambda: dict(LICENSE_FACTORS))
    exclusive_multiplier: float = DEFAULT_EXCLUSIVE
    spread: float = DEFAULT_SPREAD
    source: str = "built-in estimates"
    deals: dict = field(default_factory=dict)  # domain -> number of deals behind its rate

    def to_dict(self) -> dict:
        return {
            "domains": self.domains,
            "license": self.license,
            "exclusive_multiplier": self.exclusive_multiplier,
            "spread": self.spread,
            "source": self.source,
            "deals": self.deals,
        }


def _num(name: str, v, lo: float = 0.0, hi: float = math.inf, lo_open: bool = True) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got {v!r}") from None
    if not math.isfinite(x) or (x <= lo if lo_open else x < lo) or x > hi:
        raise ValueError(f"{name} must be {'>' if lo_open else '>='} {lo:g} and <= {hi:g}, got {v!r}")
    return x


def load_rates(path: str) -> RateCard:
    with open(path, encoding="utf-8-sig") as fh:
        doc = json.load(fh)
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: a rate card is a JSON object")
    card = RateCard(source=str(doc.get("source") or path))
    for d, r in (doc.get("domains") or {}).items():
        card.domains[str(d)] = _num(f"domains.{d}", r)
    for k, f in (doc.get("license") or {}).items():
        card.license[str(k)] = _num(f"license.{k}", f, hi=1.0)
    if "exclusive_multiplier" in doc:
        card.exclusive_multiplier = _num("exclusive_multiplier", doc["exclusive_multiplier"], lo=1.0, lo_open=False)
    if "spread" in doc:
        card.spread = _num("spread", doc["spread"], lo=0.0, hi=0.9, lo_open=False)
    card.deals = {str(k): int(v) for k, v in (doc.get("deals") or {}).items()}
    return card


def rates_from_deals(path: str) -> RateCard:
    implied: dict[str, list[float]] = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for n, row in enumerate(csv.DictReader(fh), 2):
            row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            where = f"{path} line {n}"
            domain = row.get("domain", "").lower()
            if not domain:
                raise ValueError(f"{where}: domain is empty")
            if row.get("mtokens"):
                mtok = _num(f"{where}: mtokens", row["mtokens"])
            else:
                mtok = _num(f"{where}: unique_tokens", row.get("unique_tokens")) / 1e6
            price = _num(f"{where}: price_usd", row.get("price_usd", "").replace(",", "").lstrip("$"))
            lic = row.get("license") or "clear"
            if lic not in LICENSE_FACTORS:
                raise ValueError(f"{where}: license must be one of {sorted(LICENSE_FACTORS)}")
            excl = DEFAULT_EXCLUSIVE if row.get("exclusive", "").lower() in TRUE else 1.0
            age = _num(f"{where}: age_months", row["age_months"], lo_open=False) if row.get("age_months") else 0.0
            rate = price / (mtok * LICENSE_FACTORS[lic] * excl * freshness_factor(age))
            implied.setdefault(domain, []).append(rate)
    if not implied:
        raise ValueError(f"{path}: no deals found (columns: domain, unique_tokens or mtokens, price_usd)")
    card = RateCard(source=f"{sum(map(len, implied.values()))} deals in {path}")
    for d, rates in implied.items():
        card.domains[d] = round(statistics.median(rates), 4)
        card.deals[d] = len(rates)
    # how much comparable deals disagree, as a fraction of the typical rate in each domain
    rel = [r / card.domains[d] for d, rates in implied.items() for r in rates]
    if len(rel) >= 3:
        q1, _, q3 = statistics.quantiles(rel, n=4)
        card.spread = round(min(0.9, max(0.1, (q3 - q1) / 2)), 3)
    return card
