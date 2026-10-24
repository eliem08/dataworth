"""Corpus profiling and valuation."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field, asdict

__all__ = ["DOMAIN_RATES", "LICENSE_FACTORS", "CorpusProfile", "Valuation", "scan_dir", "value_corpus"]

TEXT_EXTS = {
    ".txt", ".md", ".csv", ".tsv", ".json", ".jsonl", ".xml", ".html", ".log", ".yaml", ".yml",
    ".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".h", ".rb", ".php", ".sql", ".sh",
}

# USD per million *unique* tokens, rough market comps.
DOMAIN_RATES = {
    "web": 0.50,
    "general": 1.00,
    "support": 6.00,
    "conversational": 8.00,
    "code": 5.00,
    "scientific": 12.00,
    "legal": 15.00,
    "financial": 20.00,
    "medical": 25.00,
}

LICENSE_FACTORS = {"unclear": 0.25, "mixed": 0.60, "clear": 1.00}

CHARS_PER_TOKEN = 4


@dataclass
class CorpusProfile:
    path: str
    files: int = 0
    bytes: int = 0
    tokens: int = 0
    unique_tokens: int = 0
    by_ext: dict = field(default_factory=dict)

    @property
    def unique_ratio(self) -> float:
        return self.unique_tokens / self.tokens if self.tokens else 0.0


@dataclass
class Valuation:
    low: float
    mid: float
    high: float
    factors: dict

    def to_dict(self):
        return asdict(self)


def _est_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN) if text.strip() else 0


def scan_dir(path: str) -> CorpusProfile:
    """Walk `path`, estimate tokens and line-level duplication across all text files."""
    prof = CorpusProfile(path=path)
    seen: set[bytes] = set()
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"node_modules", "__pycache__"}]
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in TEXT_EXTS:
                continue
            full = os.path.join(root, name)
            try:
                with open(full, encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            prof.files += 1
            prof.bytes += os.path.getsize(full)
            prof.by_ext[ext] = prof.by_ext.get(ext, 0) + 1
            for line in text.splitlines():
                t = _est_tokens(line)
                if not t:
                    continue
                prof.tokens += t
                h = hashlib.blake2b(line.strip().lower().encode(), digest_size=12).digest()
                if h not in seen:
                    seen.add(h)
                    prof.unique_tokens += t
    return prof


def uniqueness_factor(ratio: float) -> float:
    if ratio >= 0.9:
        return 1.0 + (ratio - 0.9) * 2  # up to 1.2
    return max(0.2, ratio / 0.9)


def freshness_factor(age_months: float) -> float:
    if age_months <= 12:
        return 1.0
    return max(0.5, 1.0 - 0.03 * (age_months - 12))


def value_corpus(
    prof: CorpusProfile,
    domain: str = "general",
    license: str = "mixed",
    age_months: float = 0,
    exclusive: bool = False,
    spread: float = 0.35,
) -> Valuation:
    if domain not in DOMAIN_RATES:
        raise ValueError(f"unknown domain {domain!r}; choose from {sorted(DOMAIN_RATES)}")
    if license not in LICENSE_FACTORS:
        raise ValueError(f"unknown license {license!r}; choose from {sorted(LICENSE_FACTORS)}")
    factors = {
        "unique_mtokens": prof.unique_tokens / 1e6,
        "base_rate": DOMAIN_RATES[domain],
        "uniqueness": round(uniqueness_factor(prof.unique_ratio), 4),
        "license": LICENSE_FACTORS[license],
        "freshness": round(freshness_factor(age_months), 4),
        "exclusivity": 2.5 if exclusive else 1.0,
    }
    mid = 1.0
    for v in factors.values():
        mid *= v
    return Valuation(low=mid * (1 - spread), mid=mid, high=mid * (1 + spread), factors=factors)
