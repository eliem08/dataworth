# data-zestimate

[![CI](https://github.com/eliem08/data-zestimate/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/data-zestimate/actions/workflows/ci.yml)

> **Zestimate for company data** — what your data is worth to an AI lab.

AI labs are paying real money for proprietary, licensable training data
(support transcripts, code, legal filings, domain documents). Most companies
have no idea what theirs is worth. `data-zestimate` scans a corpus and gives
an instant, explainable price range — the same way a Zestimate gives a home
value before you ever talk to an agent.

## What the MVP does

- **Scans** a directory of text-like files (txt, md, csv, json, code, logs…)
- **Profiles** it: file count, bytes, estimated tokens, duplicate ratio, file mix
- **Values** it with a transparent comps model:
  - base `$ / million unique tokens` by domain (legal, medical, code, …)
  - multipliers for uniqueness, license clarity, freshness and exclusivity
  - a low / mid / high range plus an itemised breakdown of every factor

## Quickstart

```bash
pip install -e .
data-zestimate scan ./my-support-tickets --domain support --license clear --age-months 6
data-zestimate scan ./repo --domain code --exclusive --json
data-zestimate domains
```

## Model

`value = unique_tokens/1e6 × base_rate(domain) × uniqueness × license × freshness × exclusivity`

| factor | range | notes |
|---|---|---|
| uniqueness | 0.2 – 1.2 | rewards low duplication, premium above 90% unique |
| license | 0.25 / 0.6 / 1.0 | unclear / mixed / clear provenance & rights |
| freshness | 0.5 – 1.0 | decays ~3%/month after 12 months |
| exclusivity | 1.0 / 2.5 | exclusive deals command a premium |

Base rates are placeholder comps — calibrate them against real licensing deals.

## Roadmap

- Comparable-deal database (public licensing deals as comps)
- PII / secrets detection that discounts value until scrubbed
- Semantic novelty vs. Common Crawl (embedding overlap)
- "List it" — one-click data room for buyers

## Development

Zero runtime dependencies; Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m unittest discover -s tests -t .           # unit + CLI smoke tests
ruff check . && ruff format --check .               # lint + format
```

```
data_zestimate/core.py       domain logic (pure, importable, fully tested)
data_zestimate/__main__.py   CLI (`data-zestimate ...` / `python -m data_zestimate ...`)
tests/                unit tests + generated CLI smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #1).
