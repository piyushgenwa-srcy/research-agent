# Research Agent Orchestration / Harness Spec

## Purpose

This document describes the orchestration layer for the research agent. It is intentionally separate from the skill files.

Skills are reusable guidance modules. The harness is responsible for:
- selecting which skills are relevant
- deciding when to call tools or reuse existing artifacts
- validating artifacts before the agent relies on them
- revisiting earlier artifacts when contradictions appear

The harness should not assume a fixed end-to-end pipeline. It should manage a graph of working artifacts.

---

## Core Components

### 1. Agent
The central LLM pursuing the user's research goal.

### 2. Skills
Reusable guidance for recurring subproblems:
- `00a_market_assortment_intake`
- `00_client_profile`
- `01_data_extraction`
- `02_trend_discovery`
- `03_trend_synthesis`
- `04_sku_mapping`
- `05_sentiment_analysis`
- `06_demand_tier_classification`
- `07_catalog_assembly`

### 3. Tools / Connectors
- retailer page scraper or manual page fetch
- Apify social connectors
- Oxylab marketplace scraping
- SerpAPI
- TMAPI

### 4. Programmatic Validators
- required field checks
- schema validation for each artifact
- contradiction checks
- minimum evidence thresholds
- market / lane compatibility checks

### 5. Working Artifacts
- `market_assortment_context`
- `client_profile`
- `lane_evidence_pack`
- `lane_signal_output`
- `trend_candidates`
- `sku_definitions`
- `sentiment_opportunities`
- `tiered_recommendations`
- final catalog / dashboard payload

---

## Orchestration Rules

### Entry
Start from the user goal, not from a fixed skill order.

The harness should first decide:
- is there enough context to form a `client_profile`?
- did the user provide retailer/category URLs that justify `market_assortment_context`?
- which lanes matter for this client?
- does the user need sourcing recommendations, private-label differentiation, or both?

### Artifact-first routing
The harness should ask:
- which artifact is missing or too weak?
- which skill is best suited to create or refine that artifact?

Examples:
- If the brief is messy or underspecified, use `00_client_profile`.
- If retailer URLs exist and the target question is whitespace or assortment gaps, use `00a_market_assortment_intake`.
- If trend evidence is thin, use `01_data_extraction` for more lane evidence before using `03_trend_synthesis`.
- If rankings look unstable, revisit `03_trend_synthesis` or `06_demand_tier_classification` with corrected inputs.

### Parallelizable work
The harness may run these in parallel when useful:
- `01_data_extraction` across multiple lanes
- `02_trend_discovery` across multiple lanes
- supporting connector fetches for multiple categories or markets

### Conditional capabilities
The harness should treat these as optional:
- `04_sku_mapping` when the agent needs concrete sourceable formats or variants
- `05_sentiment_analysis` when product-design or private-label insight is needed

### Revisit behavior
The harness should revisit an earlier artifact when:
- required fields are missing
- evidence conflicts materially
- output size is below the minimum useful set
- saturation or margin data contradicts earlier prioritization
- a validator fails

---

## Suggested Routing Heuristics

### Rappi / quick commerce sourcing
- Usually create `client_profile`
- Use `market_assortment_context` when retailer pages are available
- Prioritize quick-commerce compatible lanes and operational fit
- Use `04_sku_mapping` when concrete sourceable formats are needed
- Usually skip `05_sentiment_analysis`

### MercadoLibre / private label
- Usually create `client_profile`
- Prioritize social + marketplace evidence
- Use `04_sku_mapping`
- Use `05_sentiment_analysis` when differentiation depends on consumer complaints or wishlists

### NocNoc / sourcing
- Usually create `client_profile`
- Use `market_assortment_context` when competitor or retailer context matters
- Use `04_sku_mapping` only when the final output requires a more concrete sourcing brief
- Usually skip `05_sentiment_analysis`

---

## Validator Expectations

Before a downstream artifact is trusted, the harness should validate:

### `client_profile`
- required fields exist
- `trend_definition` is specific
- no unresolved contradictions on platform, markets, or use case

### `lane_evidence_pack`
- evidence is source-grounded
- missing metrics are explicit
- naming ambiguity is preserved when needed

### `trend_candidates`
- lane conflicts are visible
- time-machine logic is explicit
- assortment-fit claims are backed by evidence when present

### `tiered_recommendations`
- thresholds are auditable
- proxy pricing is flagged
- conflict cases are preserved instead of hidden

---

## Common Artifact Graph

A common graph looks like:

`raw brief` -> `client_profile`  
`retailer URLs` -> `market_assortment_context`  
`connector outputs` -> `lane_evidence_pack` -> `lane_signal_output` -> `trend_candidates`  
`trend_candidates` -> `sku_definitions` / `sentiment_opportunities` / `tiered_recommendations`  
`tiered_recommendations` + supporting artifacts -> final output

This graph is descriptive, not mandatory. The harness may skip nodes, revisit nodes, or refine existing artifacts in place.
