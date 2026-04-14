# Skill: Preserve Ambiguity Before Judgment

## Use This Skill When

The agent is normalizing noisy marketplace or social inputs and the product label, naming match, or evidence relationship is uncertain.

## Problem It Solves

Agents often collapse ambiguity too early, which makes later synthesis look cleaner than the evidence actually supports.

## Core Move

Keep uncertainty explicit:
- possible alternative normalizations
- repost suspicion
- weak keyword match
- incomplete metrics
- possible duplicate-vs-distinct item ambiguity

## What To Pay Attention To

- ambiguous names
- partial metrics
- weak matching
- likely derivative content

## Common Failure Modes

- aggressive deduplication
- false confidence in naming
- treating reposts as independent evidence

## Typical Artifact Shape

Usually enriches:
- `lane_evidence_pack`

## Guardrails

- uncertainty should be visible in the artifact, not hidden in the model's private reasoning
