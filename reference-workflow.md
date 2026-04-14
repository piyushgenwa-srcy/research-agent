# Reference Workflow

This file describes a common end-to-end research run.

It is explicitly **not** a skill.
It is a reference execution pattern the harness may follow when the task matches the standard research problem.

## Typical Run

1. Build `client_profile` from the brief.
2. Build `market_assortment_context` if retailer inputs are available.
3. Gather `lane_evidence_pack` artifacts for the relevant lanes.
4. Interpret each lane into `lane_signal_output`.
5. Synthesize into `trend_candidates`.
6. Optionally create `sku_definitions`.
7. Optionally create `sentiment_opportunities`.
8. Convert evidence into `tiered_recommendations`.
9. Package into the final output.

## Why Keep This Doc

Even in an agentic system, a reference workflow is still useful for:
- onboarding humans
- debugging harness behavior
- explaining a common happy path
- checking whether an execution run skipped something surprising

## Why This Is Not A Skill

This document:
- spans the whole process
- describes a common sequence
- talks about orchestration-level ordering

That makes it a workflow or harness reference, not reusable skill guidance.
