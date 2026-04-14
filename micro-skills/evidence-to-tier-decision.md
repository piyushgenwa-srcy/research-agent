# Skill: Evidence To Tier Decision

## Use This Skill When

The agent needs to convert mixed evidence into a decision tier such as Tier 1, 2, 3, or Skip.

## Problem It Solves

Without this skill, ranking and go/no-go logic become hand-wavy and hard to audit.

## Core Move

Turn evidence into an auditable decision using:
- thresholds
- conflict handling
- visible proxy penalties
- context-specific adjustments

## What To Pay Attention To

- demand vs saturation
- margin vs feasibility
- conflict cases that should be flagged rather than auto-resolved

## Common Failure Modes

- hiding threshold logic
- treating high saturation as the same thing as strong demand
- forcing a decisive label when the evidence is conflicting

## Typical Artifact Shape

Creates or refines:
- `tiered_recommendations`

## Guardrails

- the decision should be traceable back to explicit evidence and rules
