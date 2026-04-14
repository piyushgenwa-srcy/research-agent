# Research Agent Skill Taxonomy

This document separates three things that were previously conflated:

1. **Real skills**  
   Narrow reusable guidance for recurring agent failure modes.

2. **Harness / orchestration docs**  
   Routing, validators, artifact lifecycle, and parallelism rules.

3. **Reference workflows / broad capability bundles**  
   Higher-level domain docs that explain a common run, but should not be mistaken for skills.

---

## What Counts As A Real Skill

A real skill in this repo should:
- solve one recurring subproblem
- be reusable across multiple runs or client modes
- improve agent judgment or tool use at a specific point of difficulty
- avoid owning the full end-to-end process

A real skill should not:
- declare itself as Stage N of a pipeline
- force downstream ordering
- own global routing decisions
- pretend to be the orchestrator

---

## Canonical Skill Library

The canonical narrow skill library now lives in [micro-skills](./micro-skills).

Current canonical skills:
- [brief-to-client-frame.md](./micro-skills/brief-to-client-frame.md)
- [retailer-assortment-to-market-context.md](./micro-skills/retailer-assortment-to-market-context.md)
- [preserve-ambiguity-before-judgment.md](./micro-skills/preserve-ambiguity-before-judgment.md)
- [lane-evidence-pack-builder.md](./micro-skills/lane-evidence-pack-builder.md)
- [lane-local-signal-judgment.md](./micro-skills/lane-local-signal-judgment.md)
- [cross-lane-synthesis-with-conflict-visibility.md](./micro-skills/cross-lane-synthesis-with-conflict-visibility.md)
- [abstract-signal-to-concrete-spec.md](./micro-skills/abstract-signal-to-concrete-spec.md)
- [feedback-to-differentiation-opportunity.md](./micro-skills/feedback-to-differentiation-opportunity.md)
- [proxy-data-with-visible-confidence-penalty.md](./micro-skills/proxy-data-with-visible-confidence-penalty.md)
- [evidence-to-tier-decision.md](./micro-skills/evidence-to-tier-decision.md)
- [assembly-without-rescoring.md](./micro-skills/assembly-without-rescoring.md)

---

## How The Existing `skills/` Docs Should Be Read

The existing files in [skills](./skills) are still useful, but they are no longer the best example of "what a skill is."

They should be treated as:
- broad capability bundles
- domain reference docs
- migration sources for smaller skills

They are not the ideal target abstraction for a long-term skill library.

---

## Mapping: Old Broad Docs -> New Narrow Skills

### `skills/00_client_profile.md`
Breaks into:
- `brief-to-client-frame`

### `skills/00a_market_assortment_intake.md`
Breaks into:
- `retailer-assortment-to-market-context`

### `skills/01_data_extraction.md`
Breaks into:
- `lane-evidence-pack-builder`
- `preserve-ambiguity-before-judgment`
- `proxy-data-with-visible-confidence-penalty`

### `skills/02_trend_discovery.md`
Breaks into:
- `lane-local-signal-judgment`

### `skills/03_trend_synthesis.md`
Breaks into:
- `cross-lane-synthesis-with-conflict-visibility`

### `skills/04_sku_mapping.md`
Breaks into:
- `abstract-signal-to-concrete-spec`

### `skills/05_sentiment_analysis.md`
Breaks into:
- `feedback-to-differentiation-opportunity`

### `skills/06_demand_tier_classification.md`
Breaks into:
- `evidence-to-tier-decision`
- `proxy-data-with-visible-confidence-penalty`

### `skills/07_catalog_assembly.md`
Breaks into:
- `assembly-without-rescoring`

---

## Repo Structure Going Forward

- [architecture.md](./architecture.md): system architecture
- [orchestration.md](./orchestration.md): harness behavior
- [skill-taxonomy.md](./skill-taxonomy.md): separation between real skills, harness docs, and broad reference docs
- [micro-skills](./micro-skills): canonical narrow skills
- [skills](./skills): broad reference capability docs retained for domain context

---

## Migration Principle

When a new concept is added, prefer:
- a new narrow skill if it solves a reusable subproblem
- a harness rule if it is about routing, retries, or validators
- a workflow note only if it describes a common example run

Do not add new stage-shaped docs unless there is a strong reason to preserve a legacy reference.
