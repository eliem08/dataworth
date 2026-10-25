<!-- sell-kit:start -->
# DataWorth

[![CI](https://github.com/eliem08/dataworth/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/dataworth/actions/workflows/ci.yml)

> **Know what your company's data is worth to an AI lab before you sign a licensing deal.**

**Who it's for:** Founders, CDOs and corp-dev teams fielding data-licensing offers from AI labs.

**The problem:** AI labs are buying training data, and sellers have no idea whether an offer is fair, so they leave money on the table.

**What you get:** Scan a corpus and get a low/mid/high valuation with every factor explained: unique tokens, domain, licence cleanliness, freshness and exclusivity.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install dataworth-0.1.0-py3-none-any.whl
dataworth domains
dataworth scan examples/sample-corpus --domain support --license clear
dataworth scan examples/sample-corpus --json
```

## Web app and API

Every command is also a JSON API endpoint and a browser form, served by the built-in web app.

```bash
dataworth-web --port 8000          # then open http://127.0.0.1:8000
docker build -t dataworth . && docker run -p 8000:8000 -v dataworth-data:/data dataworth
```

Endpoints: `POST /api/scan`, `POST /api/domains`, plus `GET /healthz` and `GET /api/spec` (machine-readable field list).
Files are sent as `{"name": ..., "content": ...}`, folders as `{"files": [...]}` or a base64 zip.

## Pricing

Every plan starts with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Starter** | $49 per month | Unlimited local scans; Valuation report with factor breakdown; Email support |
| **Pro** | $299 per month | Everything in Starter; Exportable buyer-ready valuation memo; Comparable-deal benchmarks; Priority support |
| **Deal Desk** | $2,500 per valuation | Analyst-reviewed valuation; Negotiation brief for your term sheet; One strategy call |

To start a trial or buy a plan, email **sales@YOUR-DOMAIN.com**.

## Licence

Proprietary. Copyright (c) 2026 eliem08. All rights reserved. Use requires a paid plan or an active trial; see [LICENSE](LICENSE).
<!-- sell-kit:end -->

## What it does

- **Scans** a directory of text-like files (txt, md, csv, json, code, logs…)
- **Profiles** it: file count, bytes, estimated tokens, duplicate ratio, file mix
- **Values** it with a transparent comps model:
  - base `$ / million unique tokens` by domain (legal, medical, code, …)
  - multipliers for uniqueness, license clarity, freshness and exclusivity
  - a low / mid / high range plus an itemised breakdown of every factor

## Quickstart

```bash
pip install -e .
dataworth scan ./my-support-tickets --domain support --license clear --age-months 6
dataworth scan ./repo --domain code --exclusive --json
dataworth domains
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
dataworth/core.py       domain logic (pure, importable, fully tested)
dataworth/__main__.py   CLI (`dataworth ...` / `python -m dataworth ...`)
tests/                unit tests + generated CLI smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #1).
