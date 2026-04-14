# Research Agent

Structured docs for an agentic product-trend research system focused on LatAm ecommerce clients such as Rappi, MercadoLibre, and cross-border sourcing operators.

This repo is currently a workflow spec and operating model, not an application codebase. The primary assets are the architecture and harness docs, a canonical narrow skill library, broader reference capability docs, and a few working research artifacts in the repo root.

## What This Is

The workflow is designed to answer a specific business question:

"Which products are emerging in US / China signals, still underpenetrated in LatAm, commercially viable to source or private-label, and worth packaging into a client-facing recommendation?"

The repo separates that work into explicit reasoning capabilities so the process is auditable and can later be operationalized in an agentic harness.

## Architecture

This repo should be read in four layers:

1. **Architecture**  
   What the system is: agent, harness, tools, validators, and working artifacts.

2. **Harness / orchestration**  
   How the agent is routed, validated, and allowed to revisit artifacts.

3. **Canonical skills**  
   Narrow reusable skills for recurring subproblems and failure modes.

4. **Reference workflows / broad bundles**  
   Useful for onboarding and context, but not the ideal abstraction for a skill library.

The agent is allowed to skip, revisit, or combine skills based on the task. A reference workflow may still exist, but it should not be confused with the skill library.

## Canonical Skill Library

The canonical narrow skill library now lives in [micro-skills](./micro-skills):

- `brief-to-client-frame`
- `retailer-assortment-to-market-context`
- `preserve-ambiguity-before-judgment`
- `lane-evidence-pack-builder`
- `lane-local-signal-judgment`
- `cross-lane-synthesis-with-conflict-visibility`
- `abstract-signal-to-concrete-spec`
- `feedback-to-differentiation-opportunity`
- `proxy-data-with-visible-confidence-penalty`
- `evidence-to-tier-decision`
- `assembly-without-rescoring`

These are the closest thing in the repo to "real skills" in the narrow agentic sense.

## Reference Run

A common happy-path run still often looks like:

1. build `client_profile`
2. build `market_assortment_context` when retailer/category inputs are available
3. gather `lane_evidence_pack` artifacts for relevant lanes
4. interpret each lane into `lane_signal_output`
5. synthesize into `trend_candidates`
6. optionally create `sku_definitions`
7. optionally create `sentiment_opportunities`
8. convert evidence into `tiered_recommendations`
9. package the final output

That is a reference pattern, not an execution contract and not the definition of the skill system.

## Skills Directory

The core docs live here:

- [architecture.md](./architecture.md)
- [orchestration.md](./orchestration.md)
- [skill-taxonomy.md](./skill-taxonomy.md)
- [reference-workflow.md](./reference-workflow.md)
- [micro-skills](./micro-skills)
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

Read the docs in this order:

1. [architecture.md](./architecture.md)
2. [orchestration.md](./orchestration.md)
3. [skill-taxonomy.md](./skill-taxonomy.md)
4. [micro-skills](./micro-skills)

The files in [skills](./skills) are now best read as broader domain reference docs or migration sources, not as the canonical narrow skill library.

## Design Principles

- Separate extraction from judgment. Data collection should behave like an analyst; trend classification should behave like a strategist.
- Keep every artifact auditable. The agent should create explicit intermediate objects that can be inspected and validated.
- Preserve ambiguity early. Resolve conflicts only when the workflow reaches the right reasoning stage.
- Treat connector data, marketplace saturation, and margin as different signal types. They should not be conflated.
- Optimize for operationalization. These docs are intended to become harness prompts, validators, schemas, and tool contracts.
- Prefer narrow skills over stage-shaped docs. If a new concept solves a reusable subproblem, it belongs in the skill library, not in a pseudo-pipeline stage.

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

These are useful as examples, but the canonical system definition now lives in the architecture, harness, taxonomy, and `micro-skills` docs.

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
