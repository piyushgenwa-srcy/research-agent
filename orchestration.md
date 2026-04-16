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

---

## Source Routing Decision Tree

Use this decision tree to select which data sources to call at each stage of the pipeline.

### Stage 1 — Surface (what is broadly trending?)

**Primary:** `fetch_tiktok_vertical` with 6-12 keyword variants.

When to use:
- Always. TikTok is the primary demand surface for fashion/lifestyle in LATAM.
- Use `period=90` for established demand, `period=30` for recency check.
- Run velocity comparison to identify accelerating vs declining keywords.

When NOT to use:
- If the category is B2B, professional tools, or commodity staples → skip TikTok.

---

### Stage 2 — Segment (who is buying and from where?)

The output of Stage 1 includes `cohort_clusters` — hashtag co-occurrence groups.

**Per cluster, route by cohort age/aesthetic signal:**

| Cluster signal | Primary source | Secondary source |
|---|---|---|
| Hashtags: gen-z, e-girl, y2k, aesthetics, streetwear, viral sound refs | TikTok vertical (already done) | Instagram (`fetch_instagram_lane`) |
| Hashtags: elegante, maternidad, casual work, capsule, minimalist, neutral | Pinterest (`fetch_pinterest_lane`) | Instagram (`fetch_instagram_lane`) |
| Hashtags: playa, verano, vacaciones, resort, beach | TikTok vertical (already done) | Pinterest |
| Hashtags with geographic signal (e.g. mxmode, arfashion) | Repeat `fetch_tiktok_vertical` with geo-specific keywords | ML regional search |

**Rule:** Call `fetch_instagram_lane` when you need cross-cohort validation or when a cluster shows ambiguous age signal.  
**Rule:** Call `fetch_pinterest_lane` when at least one cluster has hashtags consistent with 28-45 cohort OR when TikTok STR is low but Instagram/Pinterest demand may still exist.

---

### Stage 3 — Validate (is the trend format-specific or generic?)

After segmentation, pick the top 3-5 TikTok posts by `save_to_view_ratio` per cluster.

- Read `desc` (video caption) and `top_liked_comments` for product descriptors.
- Look for: specific product format (e.g. "wrap dress", "wide-leg"), material cues, colour mentions.
- If comments show `want_to_buy` + `size_query` together → high purchase intent → proceed to supply check.
- If comments are mostly `compliment` with no `size_query` or `want_to_buy` → aspirational; lower immediate demand.

---

### Stage 4 — Supply check (does ML stock it?)

**Use:** `fetch_mercadolibre_lane` for each validated format/keyword.

- Run with both `market=MX` and `market=AR` when the brief covers both.
- Check listing count in the evidence pack.
- Then call `score_supply_gap` to compute gap scores per cohort cluster.

**Tier A gap (score ≥ 0.7):** Strong sourcing signal — proceed to SKU mapping.  
**Tier B gap (0.4–0.7):** Monitor — validate with pricing and review depth.  
**Tier C gap (< 0.4):** Supply meets demand — deprioritise unless differentiation angle exists.

---

### Stage 5 — Differentiation (what complaint or wishlist is unmet?)

Use when: use_case is `private_label` or `white_label`, OR when a Tier A gap exists.

- Read `demand_signals.complaint_samples` and `demand_signals.want_to_buy_samples` from tiktok_vertical_signal.
- Look for repeated pain points: sizing, material quality, colour availability, price ceiling.
- Cross-reference with ML review text (if available) for the same complaint pattern.

**Rule:** A complaint that appears in both TikTok comments AND ML reviews is a confirmed differentiation opportunity.

---

### Stage 6 — Confidence scoring

Before writing `tiered_recommendations`, score each candidate on 5 axes:

| Axis | Strong | Weak |
|---|---|---|
| Demand strength | Multiple keywords + hashtag cluster, high STR | Single keyword, low STR |
| Cohort clarity | One dominant cluster (clear target) | Mixed clusters, no clear winner |
| Supply gap | Tier A or B | Tier C |
| Trend velocity | Accelerating or stable | Declining |
| Format feasibility | Specific product format identified | Generic category only |

Tier 1 (actionable) = strong on 4-5 axes.  
Tier 2 (watch) = strong on 2-3 axes.  
Tier 3 (deferred) = strong on 0-1 axes.

---

### Quick connector reference

| Source | Tool | Best for | Avoid when |
|---|---|---|---|
| TikTok breadth+depth | `fetch_tiktok_vertical` | Primary demand signal, all cohorts | B2B, commodities |
| MercadoLibre | `fetch_mercadolibre_lane` | Supply check, pricing, review depth | No format hypothesis yet |
| Instagram (SerpAPI) | `fetch_instagram_lane` | Cross-cohort validation, captions | Primary demand signal (no engagement data) |
| Pinterest (SerpAPI) | `fetch_pinterest_lane` | 28-45 cohort, aspirational aesthetics | Gen-Z or viral/sound-driven trends |
| Amazon | `fetch_amazon_lane` | Generic format validation, global early movers | LATAM-specific or fast-fashion categories |
| Supply-gap scorer | `score_supply_gap` | Whitespace ranking across clusters | Before tiktok_vertical + ML data exists |
