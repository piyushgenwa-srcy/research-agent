# Skill: Lane-Local Signal Judgment

## Use This Skill When

The agent has one lane's evidence pack and needs to decide which candidates qualify as meaningful signals inside that lane.

## Problem It Solves

Without this skill, lane-local judgments get blurred together with cross-lane synthesis.

## Core Move

Interpret a single lane's evidence into `lane_signal_output`:
- does it qualify for this client's signal definition
- how strong is it in this lane
- is it emerging, declining, or saturated in this lane's view

## What To Pay Attention To

- source-specific evidence quality
- client signal definition
- native indicators of early vs late momentum

## Common Failure Modes

- cross-lane reasoning sneaking in too early
- treating reposts as independent strength
- calling weak single-post noise a real signal

## Typical Artifact Shape

Creates or refines:
- `lane_signal_output`

## Guardrails

- keep judgments local to the lane
- preserve uncertainty and conflict for synthesis
