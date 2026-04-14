# Skill: Proxy Data With Visible Confidence Penalty

## Use This Skill When

A required numeric input is unavailable and the agent must use a proxy, estimate, or fallback.

## Problem It Solves

Without this skill, agents either hallucinate precision or hide degraded confidence.

## Core Move

Use the proxy, but make the degradation explicit:
- note the proxy source
- note why the true value is missing
- carry a confidence penalty forward
- prevent the proxy from being mistaken for primary evidence

## What To Pay Attention To

- whether the proxy is directionally useful
- where the proxy should affect confidence or tiering
- audit visibility

## Common Failure Modes

- silent substitution
- proxy values presented as real measurements
- no downstream confidence penalty

## Typical Artifact Shape

Usually enriches:
- `lane_evidence_pack`
- `trend_candidates`
- `tiered_recommendations`

## Guardrails

- proxy usage must be visible anywhere it influences ranking or output
