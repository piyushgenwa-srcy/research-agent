# Research Agent

Structured skill definitions for a product-trend research workflow focused on LatAm ecommerce clients such as Rappi, MercadoLibre, and cross-border sourcing operators.

This repo is currently a workflow spec and operating model, not an application codebase. The primary assets are the markdown skill docs in [skills](./skills), plus a few working research artifacts and sample outputs in the repo root.

## What This Is

The workflow is designed to answer a specific business question:

"Which products are emerging in US / China signals, still underpenetrated in LatAm, commercially viable to source or private-label, and worth packaging into a client-facing recommendation?"

The repo separates that work into explicit reasoning stages so the process is auditable and can later be operationalized in an orchestrator.

## Workflow

The current pipeline is:

1. `00_client_profile`  
   Parse a freeform client brief into a structured `client_profile`.

2. `01_data_extraction`  
   Gather lane-specific evidence packs from source data without making trend judgments.

3. `02_trend_discovery`  
   Evaluate each lane independently and identify candidate trend signals.

4. `03_trend_synthesis`  
   Merge lane outputs, score them, and apply the time-machine filter.

5. `04_sku_mapping`  
   Convert shortlisted trends into sourceable SKU definitions.

6. `05_sentiment_analysis`  
   Extract buyer complaints, likes, and wishlist signals for product opportunity design.

7. `06_demand_tier_classification`  
   Combine trend strength, saturation, and margin into Tier 1 / 2 / 3 / Skip.

8. `07_catalog_assembly`  
   Package final outputs as client-facing catalogs or dashboard-ready payloads.

## Skills Directory

The core docs live here:

- [skills/00_client_profile.md](./skills/00_client_profile.md)
- [skills/01_data_extraction.md](./skills/01_data_extraction.md)
- [skills/02_trend_discovery.md](./skills/02_trend_discovery.md)
- [skills/03_trend_synthesis.md](./skills/03_trend_synthesis.md)
- [skills/04_sku_mapping.md](./skills/04_sku_mapping.md)
- [skills/05_sentiment_analysis.md](./skills/05_sentiment_analysis.md)
- [skills/06_demand_tier_classification.md](./skills/06_demand_tier_classification.md)
- [skills/07_catalog_assembly.md](./skills/07_catalog_assembly.md)
- [skills/data_mapping.md](./skills/data_mapping.md)

## Design Principles

- Separate extraction from judgment. Data collection should behave like an analyst; trend classification should behave like a strategist.
- Keep every stage auditable. Each skill should pass explicit structured output to the next stage.
- Preserve ambiguity early. Resolve conflicts only when the workflow reaches the right reasoning stage.
- Treat connector data, marketplace saturation, and margin as different signal types. They should not be conflated.
- Optimize for operationalization. These docs are intended to become orchestrator prompts, schemas, and tool contracts.

## Source Lanes

The workflow currently assumes four primary trend-discovery lanes:

- `tiktok`
- `instagram`
- `amazon`
- `xiaohongshu`

Supporting commercial validation sources include:

- Google Trends via SerpAPI
- MercadoLibre listing counts via Oxylab
- sourcing price inputs via TMAPI or fallback proxy logic

See [skills/data_mapping.md](./skills/data_mapping.md) for the full source-to-skill map and known gaps.

## Typical Client Modes

The workflow branches depending on the client:

- `Rappi` / quick-commerce sourcing  
  Emphasis on fast-deliverable, impulse, operational, and sourcing-feasible products.

- `MercadoLibre` / private-label or white-label  
  Emphasis on trend translatability, assortment logic, sentiment-driven product opportunity, and dashboard output.

- `NocNoc`-style sourcing  
  Emphasis on cross-border product opportunity and sourcing viability with fewer product-design steps.

## Repo Contents

Besides the skills folder, the repo currently contains working notes and example artifacts such as:

- session context notes
- raw research notes
- CSV opportunity exports
- product feedback references

These are useful as examples, but the markdown files in `skills/` are the canonical workflow definition.

## Suggested Next Steps

If this is being shared with engineering or operations, the most useful follow-on docs would be:

1. a strict JSON schema for each skill output
2. an orchestrator spec showing execution order, branching, and retries
3. a connector contract doc for Apify, Oxylab, SerpAPI, TMAPI, and related sources

## Status

Current state: workflow specification and prompt architecture.

Not yet included:

- production orchestrator code
- validated schemas
- automated connector wrappers in this repo
- test fixtures for each skill stage
