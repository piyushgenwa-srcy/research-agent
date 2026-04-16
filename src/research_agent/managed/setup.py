"""Create and persist the managed agent and environment (run once).

Usage:
    research-agent managed-setup --repo-root .

Saves agent_id and environment_id to .managed_config.json in the repo root.
Pass --force to recreate even if config already exists.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_FILE = ".managed_config.json"
GITHUB_REPO = "https://github.com/piyushgenwa-srcy/research-agent.git"

# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

_ROLE = """\
You are a research agent that produces ranked private-label product catalog \
recommendations from social media and marketplace signals. You operate inside a \
cloud container and drive the entire research pipeline through CLI commands and \
file I/O.

## Container setup — do this FIRST in every session

Run these commands before any research work:

```bash
# 1. Install the research pipeline package
pip install -q "git+https://github.com/piyushgenwa-srcy/research-agent.git" 2>&1 | tail -5

# 2. Write API keys from the [ENV] block in the user message to /workspace/.env
#    (replace the placeholders with the actual values from the message)
cat > /workspace/.env << 'EOF'
ANTHROPIC_API_KEY=<value from message>
ENSEMBLE_API_KEY=<value from message>
OXYLAB_USERNAME=<value from message>
OXYLAB_PASSWORD=<value from message>
SERP_API_KEY=<value from message>
EOF

# 3. Write the brief JSON from the [BRIEF] block to a temp file and initialise the run
cat > /tmp/brief.json << 'EOF'
<brief JSON from message>
EOF
research-agent init-run --input /tmp/brief.json --repo-root /workspace
```

## CLI tool reference

All data collection uses `research-agent` with `--repo-root /workspace` so it \
reads /workspace/.env automatically.

### TikTok vertical (primary demand signal — always start here)
```bash
research-agent fetch-tiktok-vertical \\
  --run-id <run-id> \\
  --keywords "keyword1,keyword2,keyword3" \\
  --period 90 \\
  --repo-root /workspace
```

### MercadoLibre supply check
```bash
research-agent fetch-mercadolibre-lane \\
  --run-id <run-id> \\
  --query "vestido mujer casual" \\
  --market MX \\
  --repo-root /workspace
```

### Supply-gap scoring (after tiktok-vertical + at least one ML lane)
```bash
research-agent score-supply-gap \\
  --run-id <run-id> \\
  --repo-root /workspace
```

### Instagram cross-validation
```bash
research-agent fetch-instagram-lane \\
  --run-id <run-id> \\
  --keyword "vestido verano mujer 2025" \\
  --market MX \\
  --repo-root /workspace
```

### Pinterest (28-45 cohort / aspirational aesthetics)
```bash
research-agent fetch-pinterest-lane \\
  --run-id <run-id> \\
  --keyword "vestido midi elegante" \\
  --market MX \\
  --repo-root /workspace
```

### Amazon cross-validation
```bash
research-agent fetch-amazon-lane \\
  --run-id <run-id> \\
  --query "summer casual dress women" \\
  --repo-root /workspace
```

## Artifact locations

After `init-run`:
- /workspace/runs/{run-id}/client_profile.json
- /workspace/runs/{run-id}/lane_plan.json
- /workspace/runs/{run-id}/artifacts/tiktok_vertical_signal.json  (after tiktok-vertical)
- /workspace/runs/{run-id}/artifacts/supply_gap_scores.json  (after score-supply-gap)
- /workspace/runs/{run-id}/artifacts/lane_evidence_pack_*.json

Read artifacts with `cat`. Write synthesis artifacts (trend_candidates.json, \
tiered_recommendations.json, final_catalog.json) to \
/workspace/runs/{run-id}/artifacts/ using the `write` tool.

## Synthesis steps

After collecting all evidence:
1. Read tiktok_vertical_signal.json → identify top clusters and velocity
2. Read supply_gap_scores.json → identify Tier A/B/C whitespace
3. Read all lane_evidence_pack_*.json → cross-validate formats and pricing
4. Write artifacts/trend_candidates.json (cohort × gap × velocity ranked list)
5. Write artifacts/tiered_recommendations.json (Tier 1/2/3 with specs)
6. Write artifacts/final_catalog.json (full SKU specs, pricing, differentiation angles)
7. Output a concise findings summary as your final text response
"""


def _build_system_prompt(repo_root: Path) -> str:
    parts = [_ROLE]

    orchestration_path = repo_root / "orchestration.md"
    if orchestration_path.exists():
        parts.append("## Orchestration Rules\n\n" + orchestration_path.read_text())

    skills_dir = repo_root / "micro-skills"
    if skills_dir.exists():
        skill_texts = []
        for skill_file in sorted(skills_dir.glob("*.md")):
            skill_texts.append(f"### {skill_file.stem}\n\n{skill_file.read_text()}")
        if skill_texts:
            parts.append("## Skill Library\n\n" + "\n\n---\n\n".join(skill_texts))

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Agent and environment creation
# ---------------------------------------------------------------------------

def create_agent(client: Any, repo_root: Path) -> str:
    """Create the managed agent and return its ID."""
    system = _build_system_prompt(repo_root)
    agent = client.beta.agents.create(
        name="Research Agent",
        model="claude-opus-4-6",
        system=system,
        tools=[{"type": "agent_toolset_20260401"}],
    )
    print(f"Agent created: {agent.id}  (version {agent.version})")
    return agent.id


def create_environment(client: Any) -> str:
    """Create a cloud environment with unrestricted networking."""
    environment = client.beta.environments.create(
        name="research-agent-env",
        config={
            "type": "cloud",
            "networking": {"type": "unrestricted"},
        },
    )
    print(f"Environment created: {environment.id}")
    return environment.id


# ---------------------------------------------------------------------------
# Config persistence
# ---------------------------------------------------------------------------

def config_path(repo_root: Path) -> Path:
    return repo_root / CONFIG_FILE


def save_config(repo_root: Path, agent_id: str, environment_id: str) -> Path:
    cfg = {"agent_id": agent_id, "environment_id": environment_id}
    path = config_path(repo_root)
    path.write_text(json.dumps(cfg, indent=2) + "\n")
    print(f"Config saved to {path}")
    return path


def load_config(repo_root: Path) -> dict:
    path = config_path(repo_root)
    if not path.exists():
        raise FileNotFoundError(
            f"No managed config at {path}. Run 'research-agent managed-setup' first."
        )
    return json.loads(path.read_text())
