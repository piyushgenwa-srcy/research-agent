# Skill: Cross-Lane Synthesis With Conflict Visibility

## Use This Skill When

The agent needs to merge multiple lane-local signal views into a ranked opportunity set.

## Problem It Solves

Without this skill, agents either:
- overcount repeated evidence
- hide source conflicts
- collapse leading and lagging indicators into one undifferentiated score

## Core Move

Produce `trend_candidates` by:
- deduplicating carefully
- weighting sources appropriately
- preserving per-lane evidence
- surfacing conflict instead of resolving it silently

## What To Pay Attention To

- leading vs lagging sources
- source weighting
- dedupe confidence
- conflict notes
- context-fit and assortment-fit filters

## Common Failure Modes

- treating all sources as equally independent
- hiding disagreements
- ranking only by loudness

## Typical Artifact Shape

Creates or refines:
- `trend_candidates`

## Guardrails

- conflict visibility beats premature consensus
