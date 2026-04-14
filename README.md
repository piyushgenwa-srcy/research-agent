# Research Agent

Structured skill definitions for an agentic product-trend research system focused on LatAm ecommerce clients such as Rappi, MercadoLibre, and cross-border sourcing operators.

This repo is currently a workflow spec and operating model, not an application codebase. The primary assets are the markdown skill docs in [skills](./skills), plus a few working research artifacts and sample outputs in the repo root.

## What This Is

The workflow is designed to answer a specific business question:

"Which products are emerging in US / China signals, still underpenetrated in LatAm, commercially viable to source or private-label, and worth packaging into a client-facing recommendation?"

The repo separates that work into explicit reasoning capabilities so the process is auditable and can later be operationalized in an agentic harness.

## Architecture

This repo should be read in two layers:

1. **Skills**  
   Reusable guidance modules the agent can apply when it needs help solving a specific subproblem, such as profiling a client, extracting lane evidence, or classifying demand.

2. **Orchestration / harness**  
   The layer that decides which skills to use, in what order, with which tools, validators, and retry logic.

The skills are not intended to be read as a rigid mandatory pipeline. A common run may touch several of them in a familiar order, but the agent is allowed to skip, revisit, or combine skills based on the task.

## Reference Run

A common happy-path run often looks like:

1. `00a_market_assortment_intake` when retailer/category URLs are supplied
2. `00_client_profile` to form the research frame
3. `01_data_extraction` and `02_trend_discovery` across one or more lanes
4. `03_trend_synthesis` to unify and rank opportunities
5. optional `04_sku_mapping` and `05_sentiment_analysis`
6. `06_demand_tier_classification`
7. `07_catalog_assembly`

That is a reference pattern, not an execution contract.

## Skills Directory

The core docs live here:

- [architecture.md](./architecture.md)
- [orchestration.md](./orchestration.md)
- [skills/00a_market_assortment_intake.md](./skills/00a_market_assortment_intake.md)
- [skills/00_client_profile.md](./skills/00_client_profile.md)
- [skills/01_data_extraction.md](./skills/01_data_extraction.md)
- [skills/02_trend_discovery.md](./skills/02_trend_discovery.md)
- [skills/03_trend_synthesis.md](./skills/03_trend_synthesis.md)
- [skills/04_sku_mapping.md](./skills/04_sku_mapping.md)
- [skills/05_sentiment_analysis.md](./skills/05_sentiment_analysis.md)
- [skills/06_demand_tier_classification.md](./skills/06_demand_tier_classification.md)
- [skills/07_catalog_assembly.md](./skills/07_catalog_assembly.md)
- [skills/data_mapping.md](./skills/data_mapping.md)

`architecture.md` shows the agent / harness / artifact model. `orchestration.md` is the harness-level doc. The files in `skills/` are capability guides, not pipeline nodes.

## Design Principles

- Separate extraction from judgment. Data collection should behave like an analyst; trend classification should behave like a strategist.
- Keep every artifact auditable. The agent should create explicit intermediate objects that can be inspected and validated.
- Preserve ambiguity early. Resolve conflicts only when the workflow reaches the right reasoning stage.
- Treat connector data, marketplace saturation, and margin as different signal types. They should not be conflated.
- Optimize for operationalization. These docs are intended to become harness prompts, validators, schemas, and tool contracts.

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
  Emphasis on fast-deliverable, impulse, operational, and sourcing-feasible products. When retailer URLs are supplied, start with `00a_market_assortment_intake` to ground recommendations in current shelf coverage.

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
2. a harness spec showing routing, branching, and retries
3. a connector contract doc for Apify, Oxylab, SerpAPI, TMAPI, and related sources

## Status

Current state: workflow specification and prompt architecture.

Not yet included:

- production orchestrator code
- validated schemas
- automated connector wrappers in this repo
- test fixtures for each skill stage
