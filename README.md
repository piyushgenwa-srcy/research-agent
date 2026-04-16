# Research Agent

An agentic product-trend research pipeline that turns social media signals into private-label sourcing recommendations. Given a brief, it autonomously collects evidence from TikTok, Instagram, Pinterest, MercadoLibre, and Amazon — then synthesises tiered SKU recommendations with specs, pricing, and differentiation angles.

## What it does

1. Reads a research brief → builds a `client_profile` and `lane_plan`
2. Fetches evidence across configured lanes (TikTok, ML, Amazon, Instagram, Pinterest)
3. Clusters TikTok posts into cohort segments via hashtag co-occurrence
4. Computes trend velocity (30-day vs 90-day save-to-view ratio)
5. Scores supply-demand gaps per cohort against marketplace listings
6. Classifies comments with Haiku 4.5 (purchase intent, complaints, want-to-buy)
7. Writes `trend_candidates` → `tiered_recommendations` → `final_catalog`

Completed runs produce a structured JSON catalog ready for a buyer or a presentation layer.

## Setup

**Requirements:** Python 3.9+, pip

```bash
git clone <repo>
cd research-agent
pip install -e .
cp .env.example .env   # fill in your API keys
```

**Check connector status:**
```bash
research-agent connector-status --repo-root .
```

## Running a research pipeline

**1. Initialise a run from a JSON brief:**
```bash
research-agent init-run --input examples/mercadolibre_fashion_request.json --repo-root .
```
Creates `runs/<run-id>/` with `client_profile.json`, `lane_plan.json`, `raw_brief.md`.

**2. Run the full agentic pipeline:**
```bash
research-agent run-agent --run-id mercadolibre-fashion-2026-04-16 --repo-root .
```
The agent drives all data collection and synthesis autonomously. Writes intermediate artifacts to `runs/<run-id>/artifacts/` and prints a findings summary when done.

**3. Run individual lanes manually:**
```bash
research-agent fetch-tiktok-vertical --run-id <id> --keywords "vestido mujer,vestido casual,summer dress" --repo-root .
research-agent fetch-mercadolibre-lane --run-id <id> --query "vestido mujer casual" --market MX --repo-root .
research-agent fetch-instagram-lane   --run-id <id> --keyword "vestido verano mujer 2025" --repo-root .
research-agent fetch-pinterest-lane   --run-id <id> --keyword "vestido midi elegante" --repo-root .
research-agent fetch-amazon-lane      --run-id <id> --query "summer casual dress women" --repo-root .
```

## Run request format

See [`examples/mercadolibre_fashion_request.json`](./examples/mercadolibre_fashion_request.json) for a complete example. Key fields:

```json
{
  "run_id": "my-run-2026-04-16",
  "client_name": "Acme",
  "platform": "mercadolibre",
  "raw_brief": "...",
  "markets": ["MX", "AR"],
  "categories": ["dresses", "athleisure"],
  "price_bracket": "mid-market",
  "use_case": "private_label",
  "moq": 50,
  "min_products": 6,
  "max_products": 12
}
```

## Source code

```
src/research_agent/
├── agent.py              # agentic loop (Claude Opus 4.6 + tool use)
├── harness.py            # data-fetching orchestration
├── cli.py                # CLI entrypoints
├── tiktok_vertical.py    # two-pass TikTok collection + cohort clustering + velocity
├── comment_classifier.py # Haiku 4.5 comment classification (falls back to regex)
├── supply_gap.py         # demand × supply gap scorer
├── extractors.py         # evidence pack builders for all lanes
├── models.py             # typed artifact models
├── config.py             # env loading + connector status
├── artifact_io.py        # JSON read/write helpers
├── validators.py         # artifact validation
└── connectors/
    ├── ensemble.py       # TikTok via Ensemble Data API
    ├── oxylabs.py        # MercadoLibre + Amazon via Oxylabs
    ├── serpapi.py        # Instagram + Pinterest via SerpAPI Google search
    └── base.py           # shared HTTP helpers
```

## Connectors

| Connector | Provider | Used for | Required |
|---|---|---|---|
| Ensemble | [ensembledata.com](https://ensembledata.com) | TikTok keyword search, hashtag posts, post comments | Yes |
| Oxylabs | [oxylabs.io](https://oxylabs.io) | MercadoLibre + Amazon scraping | Yes |
| SerpAPI | [serpapi.com](https://serpapi.com) | Instagram + Pinterest via `site:` Google search | Yes |
| Anthropic | [anthropic.com](https://anthropic.com) | Agent loop (Claude Opus 4.6) + comment classifier (Haiku 4.5) | Yes |
| TMAPI | — | Marketplace data (stub, not yet wired) | No |
| JungleScout | — | Amazon demand volume (stub, not yet wired) | No |

Copy `.env.example` → `.env` and fill in keys for the four required connectors.

## Artifacts produced per run

| File | Description |
|---|---|
| `client_profile.json` | Client frame derived from brief |
| `lane_plan.json` | Which lanes to run and why |
| `artifacts/tiktok_vertical_signal.json` | Full TikTok breadth + depth output with cohort clusters and velocity |
| `artifacts/supply_gap_scores.json` | Per-cohort demand vs supply gap scores (Tier A/B/C) |
| `artifacts/lane_evidence_pack_*.json` | Raw evidence packs per lane |
| `artifacts/trend_candidates.json` | Synthesised candidates with tier and evidence |
| `artifacts/tiered_recommendations.json` | Scored recommendations |
| `artifacts/final_catalog.json` | Final structured catalog with full SKU specs |

## Agent tools

The agent loop has access to these tools:

- `list_artifacts` / `read_artifact` / `write_artifact` — run directory I/O
- `fetch_tiktok_vertical` — two-pass TikTok collection (breadth + comment depth)
- `fetch_mercadolibre_lane` — ML scraping via Oxylabs
- `fetch_amazon_lane` — Amazon scraping via Oxylabs
- `fetch_instagram_lane` — Instagram signal via SerpAPI
- `fetch_pinterest_lane` — Pinterest signal via SerpAPI
- `fetch_tiktok_lane` — single-keyword TikTok (lightweight, use vertical for deep runs)
- `score_supply_gap` — cross-reference TikTok demand vs ML supply per cohort

## Orchestration + skills

[`orchestration.md`](./orchestration.md) contains the source routing decision tree (6 stages: Surface → Segment → Validate → Supply check → Differentiation → Confidence scoring) and quick connector reference. The agent reads this at runtime.

Reusable reasoning skills live in [`micro-skills/`](./micro-skills/).
