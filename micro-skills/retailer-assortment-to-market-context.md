# Skill: Retailer Assortment To Market Context

## Use This Skill When

The agent has retailer URLs, category pages, storefront exports, or other competitor assortment inputs and needs to turn them into current-market context.

## Problem It Solves

Without this skill, the agent treats market whitespace as a guess rather than a grounded view of what is already on shelf.

## Core Move

Convert retailer/category evidence into `market_assortment_context`:
- coverage by retailer
- assortment depth
- whitespace hypotheses
- over-covered formats
- retailer archetypes

## What To Pay Attention To

- shelf presence is not demand
- "missing from this sample" is only a hypothesis
- preserve retailer asymmetry
- normalize branded references into sourceable formats where useful

## Common Failure Modes

- overstating gaps
- averaging away retailer differences
- confusing sparse evidence with true whitespace

## Typical Artifact Shape

Creates or refines:
- `market_assortment_context`

## Guardrails

- gap claims need evidence
- confidence should drop when page coverage is thin or partial
