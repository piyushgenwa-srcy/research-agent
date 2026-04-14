# Skill: Assembly Without Rescoring

## Use This Skill When

The agent needs to turn vetted recommendations into a client-facing deliverable.

## Problem It Solves

Agents often treat output assembly as another reasoning stage and silently change priorities while formatting.

## Core Move

Package recommendations into the requested format while preserving:
- tiers
- conflict flags
- proxy visibility
- provenance

## What To Pay Attention To

- grouping logic
- output readability
- appendix vs main-body separation
- no hidden reprioritization

## Common Failure Modes

- rescoring during formatting
- burying conflicts
- padding outputs with weak items to hit quotas

## Typical Artifact Shape

Creates or refines:
- final catalog / dashboard payload / memo

## Guardrails

- output assembly is packaging, not decision rewriting
