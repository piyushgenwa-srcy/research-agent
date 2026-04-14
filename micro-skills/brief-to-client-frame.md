# Skill: Brief To Client Frame

## Use This Skill When

The agent needs to turn a messy client brief into a structured working frame with explicit markets, categories, buyer logic, constraints, and research intent.

## Problem It Solves

Without this skill, agents either:
- over-infer from vague briefs
- miss critical constraints
- leave the trend definition too generic to guide later reasoning

## Core Move

Convert freeform brief text into a `client_profile` artifact with:
- explicit fields
- logged inferences
- surfaced contradictions
- a specific "what counts as a signal" definition

## What To Pay Attention To

- infer defaults only when platform context strongly supports them
- keep required fields explicit
- separate stated facts from inferred facts
- make the trend definition specific enough to guide evidence collection
- emit routing hints, not execution orders

## Common Failure Modes

- vague trend definitions like "popular products"
- silently guessed markets or categories
- mixing routing logic into the artifact itself
- treating missing information as harmless

## Typical Artifact Shape

Creates or refines:
- `client_profile`

## Guardrails

- never guess a required field when the cost of being wrong is high
- contradiction visibility beats forced resolution
- the output should be usable by the harness and by downstream reasoning artifacts
