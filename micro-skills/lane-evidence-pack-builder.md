# Skill: Lane Evidence Pack Builder

## Use This Skill When

The agent needs a source-grounded evidence pack for one lane such as TikTok, Amazon, Instagram, or Xiaohongshu.

## Problem It Solves

Without this skill, the agent jumps too quickly from raw connector output to conclusions.

## Core Move

Produce a normalized `lane_evidence_pack` containing:
- source-native facts
- normalized labels
- explicit nulls for missing metrics
- excluded-item log
- short factual notes

## What To Pay Attention To

- evidence provenance
- metric completeness
- off-category noise
- keeping the pack useful for later audit

## Common Failure Modes

- mixing evidence collection with trend judgment
- silently dropping noisy results
- inventing missing values

## Typical Artifact Shape

Creates or refines:
- `lane_evidence_pack`

## Guardrails

- this skill gathers evidence, it does not decide whether a signal is real
