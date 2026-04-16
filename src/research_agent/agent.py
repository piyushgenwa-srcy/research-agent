"""Agentic research loop powered by Claude.

The agent drives the full research pipeline autonomously:
  1. Reads existing artifacts (client_profile, lane_plan).
  2. Decides which lanes to fetch based on the client frame.
  3. Calls fetch tools to collect evidence packs.
  4. Writes synthesised artifacts (lane_signal_output, trend_candidates,
     tiered_recommendations, final_catalog) using micro-skill guidance
     injected into the system prompt.
  5. Returns a concise findings summary.

Usage (CLI):
    research-agent run-agent --run-id mercadolibre-2026-04-14

Usage (Python):
    from research_agent.agent import run_agent
    from research_agent.config import Settings
    summary = run_agent("mercadolibre-2026-04-14", Settings.load(), Path("."))
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from .artifact_io import write_json
from .config import Settings
from .harness import Harness

try:
    import anthropic as _anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

MODEL = "claude-opus-4-6"
MAX_TOKENS = 16_000
MAX_ITERATIONS = 30

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "list_artifacts",
        "description": (
            "List all artifacts currently present in the run directory. "
            "Call this first to understand what has already been built."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string", "description": "Run ID"}
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "read_artifact",
        "description": (
            "Read a specific artifact from the run directory. "
            "Use this to read client_profile.json, lane_plan.json, "
            "evidence packs under artifacts/, or any previously written artifact."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "artifact_name": {
                    "type": "string",
                    "description": (
                        "Path relative to the run directory, e.g. "
                        "'client_profile.json' or 'artifacts/lane_evidence_pack_amazon_home.json'"
                    ),
                },
            },
            "required": ["run_id", "artifact_name"],
        },
    },
    {
        "name": "write_artifact",
        "description": (
            "Write a synthesised artifact to the run directory. "
            "Use this to persist lane_signal_output, trend_candidates, "
            "tiered_recommendations, or the final_catalog. "
            "The content must be a JSON object."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "artifact_name": {
                    "type": "string",
                    "description": "Filename to write, e.g. 'trend_candidates.json'",
                },
                "content": {
                    "type": "object",
                    "description": "Artifact content as a structured JSON object.",
                },
            },
            "required": ["run_id", "artifact_name", "content"],
        },
    },
    {
        "name": "fetch_amazon_lane",
        "description": (
            "Fetch an Amazon lane evidence pack via Oxylabs. "
            "Use for marketplace cross-validation of product formats and "
            "early-mover ranking signals. Requires Oxylabs credentials."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "query": {
                    "type": "string",
                    "description": "Amazon search query, e.g. 'home organization products'",
                },
            },
            "required": ["run_id", "query"],
        },
    },
    {
        "name": "fetch_tiktok_lane",
        "description": (
            "Fetch a TikTok lane evidence pack via Ensemble. "
            "Use for social trend signals. Requires Ensemble credentials."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "keyword": {
                    "type": "string",
                    "description": "TikTok search keyword, e.g. 'home decor organization'",
                },
            },
            "required": ["run_id", "keyword"],
        },
    },
    {
        "name": "fetch_mercadolibre_lane",
        "description": (
            "Fetch a MercadoLibre lane evidence pack via Oxylabs universal scraper. "
            "Use for current assortment baseline, whitespace identification, "
            "and review-driven differentiation signals. Requires Oxylabs credentials."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "query": {
                    "type": "string",
                    "description": "MercadoLibre search keyword, e.g. 'organizador hogar'",
                },
                "market": {
                    "type": "string",
                    "description": "ISO market code: MX (default), AR, BR, CO, CL",
                    "enum": ["MX", "AR", "BR", "CO", "CL"],
                },
            },
            "required": ["run_id", "query"],
        },
    },
    {
        "name": "fetch_tiktok_vertical",
        "description": (
            "Two-pass vertical TikTok signal collection for a single category. "
            "Pass 1 (breadth): paginate multiple keywords + expand top hashtags → pool of 300-800 posts scored by save-to-view ratio. "
            "Pass 2 (depth): fetch comments on top-20 posts by save-to-view → complaint extraction, want-to-buy signals, purchase intent flags. "
            "Use instead of fetch_tiktok_lane when going deep on one category. "
            "Writes artifacts/tiktok_vertical_signal.json."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "6-12 keyword variants covering the category: broad terms, specific formats, use-case phrases. Mix Spanish and English for LATAM.",
                },
                "period": {
                    "type": "integer",
                    "description": "Lookback window in days (default 90). Use 30 for very recent trends, 180 for established demand.",
                    "default": 90,
                },
                "depth_top_n": {
                    "type": "integer",
                    "description": "Number of top posts to fetch comments for (default 20).",
                    "default": 20,
                },
            },
            "required": ["run_id", "keywords"],
        },
    },
    {
        "name": "fetch_instagram_lane",
        "description": (
            "Fetch Instagram trend signals via SerpAPI Google site:instagram.com search. "
            "Returns post captions as trend signal — use for visual trend cues, hashtag clusters, "
            "and early demand signals that precede marketplace listings. Requires SerpAPI key."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "keyword": {
                    "type": "string",
                    "description": "Fashion keyword in Spanish or English, e.g. 'vestido verano mujer 2025'",
                },
                "market": {
                    "type": "string",
                    "description": "ISO market code: MX (default), AR, BR, CO, CL",
                    "enum": ["MX", "AR", "BR", "CO", "CL"],
                },
            },
            "required": ["run_id", "keyword"],
        },
    },
    {
        "name": "score_supply_gap",
        "description": (
            "Cross-reference TikTok vertical demand signal with MercadoLibre supply to score "
            "whitespace opportunities per cohort cluster. "
            "Requires artifacts/tiktok_vertical_signal.json and at least one "
            "artifacts/lane_evidence_pack_mercadolibre-*.json to exist in the run. "
            "Writes artifacts/supply_gap_scores.json. "
            "Call this after fetch_tiktok_vertical + one or more fetch_mercadolibre_lane calls."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
            },
            "required": ["run_id"],
        },
    },
    {
        "name": "fetch_pinterest_lane",
        "description": (
            "Fetch Pinterest visual trend signals via SerpAPI Google site:pinterest.com search. "
            "Best for: 28-45 cohort signals, aspirational aesthetics, early-stage category trends "
            "that precede TikTok virality. Complements TikTok vertical with older-cohort demand. "
            "Requires SerpAPI key."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "run_id": {"type": "string"},
                "keyword": {
                    "type": "string",
                    "description": "Visual/fashion keyword, e.g. 'vestido midi elegante 2025'",
                },
                "market": {
                    "type": "string",
                    "description": "ISO market code: MX (default), AR, BR, CO, CL",
                    "enum": ["MX", "AR", "BR", "CO", "CL"],
                },
            },
            "required": ["run_id", "keyword"],
        },
    },
]


# ---------------------------------------------------------------------------
# System prompt builder
# ---------------------------------------------------------------------------

def _build_system_prompt(repo_root: Path) -> List[Dict[str, Any]]:
    """Build a two-block system prompt with prompt caching on the static skills context.

    Block 1 — role framing (small, not cached).
    Block 2 — orchestration rules + micro-skills (large, stable, cached).
    """
    role_block = (
        "You are a research agent that produces ranked product catalog recommendations "
        "from social media and marketplace signals.\n\n"
        "You work by calling tools to:\n"
        "1. Read existing artifacts (client_profile, lane_plan) to understand the research brief.\n"
        "2. Fetch evidence from lanes (TikTok, Instagram, Amazon, MercadoLibre) based on the client frame.\n"
        "3. Apply skill guidance to synthesise and interpret evidence into structured artifacts.\n"
        "4. Write intermediate artifacts: lane_signal_output, trend_candidates, "
        "tiered_recommendations.\n"
        "5. Produce a final_catalog artifact and a concise findings summary.\n\n"
        "Always call list_artifacts first. Read client_profile.json and lane_plan.json before "
        "deciding which lanes to fetch. If a connector is not configured (tool returns an error), "
        "note the gap and proceed with available evidence.\n\n"
        "When you have written the final_catalog artifact, output a concise findings summary "
        "as your final text response."
    )

    static_parts: List[str] = []

    orchestration_path = repo_root / "orchestration.md"
    if orchestration_path.exists():
        static_parts.append(
            "## Orchestration Rules\n\n" + orchestration_path.read_text()
        )

    skills_dir = repo_root / "micro-skills"
    if skills_dir.exists():
        skill_texts = []
        for skill_file in sorted(skills_dir.glob("*.md")):
            skill_texts.append(f"### {skill_file.stem}\n\n{skill_file.read_text()}")
        if skill_texts:
            static_parts.append(
                "## Skill Library\n\n" + "\n\n---\n\n".join(skill_texts)
            )

    arch_path = repo_root / "architecture.md"
    if arch_path.exists():
        static_parts.append("## Artifact Graph\n\n" + arch_path.read_text())

    static_context = "\n\n".join(static_parts) if static_parts else (
        "No orchestration or skill files found in repo root."
    )

    return [
        {"type": "text", "text": role_block},
        {
            "type": "text",
            "text": static_context,
            "cache_control": {"type": "ephemeral"},
        },
    ]


# ---------------------------------------------------------------------------
# Evidence pack summariser
# ---------------------------------------------------------------------------

def _summarise_evidence_pack(pack: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact summary of an evidence pack to keep tool results manageable.

    The full pack is written to disk by the harness. The agent receives a
    summary with enough signal to drive synthesis decisions.
    """
    candidates = pack.get("candidates", [])
    top: List[Dict[str, Any]] = []
    for c in candidates[:7]:
        items = c.get("evidence_items", [{}])
        first = items[0] if items else {}
        metrics = first.get("metrics", {})
        top.append(
            {
                "name": c.get("normalized_product_name") or c.get("source_product_label"),
                "source_id": first.get("source_id"),
                "generic_format_note": c.get("generic_format_note"),
                "metrics": {k: v for k, v in metrics.items() if v is not None},
                "quality_flags": c.get("data_quality_flags", []),
            }
        )
    return {
        "lane": pack.get("lane"),
        "search_objective": pack.get("search_objective"),
        "client_scope": pack.get("client_scope", {}),
        "candidate_count": len(candidates),
        "top_candidates": top,
        "extraction_warnings": pack.get("extraction_warnings", []),
        "excluded_count": len(pack.get("excluded_items", [])),
    }


# ---------------------------------------------------------------------------
# Tool executor
# ---------------------------------------------------------------------------

def _execute_tool(
    name: str,
    inputs: Dict[str, Any],
    harness: Harness,
    runs_root: Path,
) -> Any:
    run_id: str = inputs.get("run_id", "")
    run_dir = runs_root / run_id

    if name == "list_artifacts":
        artifacts: List[str] = []
        for path in sorted(run_dir.rglob("*.json")):
            artifacts.append(str(path.relative_to(run_dir)))
        for path in sorted(run_dir.rglob("*.md")):
            if path.name != "raw_brief.md":
                artifacts.append(str(path.relative_to(run_dir)))
        return {"artifacts": artifacts, "count": len(artifacts)}

    if name == "read_artifact":
        artifact_name: str = inputs["artifact_name"]
        path = run_dir / artifact_name
        if not path.exists():
            return {"error": f"Artifact not found: {artifact_name}"}
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"content": path.read_text()}

    if name == "write_artifact":
        artifact_name = inputs["artifact_name"]
        content = inputs["content"]
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except json.JSONDecodeError:
                pass
        path = run_dir / artifact_name
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, content)
        top_keys = list(content.keys())[:8] if isinstance(content, dict) else []
        return {
            "written": artifact_name,
            "top_keys": top_keys,
        }

    if name == "fetch_amazon_lane":
        try:
            pack = harness.fetch_amazon_lane(
                run_id=run_id, query=inputs["query"], runs_root=runs_root
            )
            return _summarise_evidence_pack(pack.to_dict())
        except Exception as exc:
            return {"error": str(exc), "lane": "amazon", "query": inputs.get("query")}

    if name == "fetch_tiktok_lane":
        try:
            pack = harness.fetch_tiktok_lane(
                run_id=run_id, keyword=inputs["keyword"], runs_root=runs_root
            )
            return _summarise_evidence_pack(pack.to_dict())
        except Exception as exc:
            return {"error": str(exc), "lane": "tiktok", "keyword": inputs.get("keyword")}

    if name == "fetch_mercadolibre_lane":
        try:
            pack = harness.fetch_mercadolibre_lane(
                run_id=run_id,
                query=inputs["query"],
                market=inputs.get("market", "MX"),
                runs_root=runs_root,
            )
            return _summarise_evidence_pack(pack.to_dict())
        except Exception as exc:
            return {
                "error": str(exc),
                "lane": "mercadolibre",
                "query": inputs.get("query"),
                "market": inputs.get("market", "MX"),
            }

    if name == "fetch_tiktok_vertical":
        try:
            result = harness.fetch_tiktok_vertical(
                run_id=run_id,
                keywords=inputs["keywords"],
                period=inputs.get("period", 90),
                depth_top_n=inputs.get("depth_top_n", 20),
                runs_root=runs_root,
            )
            return result
        except Exception as exc:
            return {"error": str(exc), "tool": "fetch_tiktok_vertical"}

    if name == "fetch_instagram_lane":
        try:
            pack = harness.fetch_instagram_lane(
                run_id=run_id,
                keyword=inputs["keyword"],
                market=inputs.get("market", "MX"),
                runs_root=runs_root,
            )
            return _summarise_evidence_pack(pack.to_dict())
        except Exception as exc:
            return {
                "error": str(exc),
                "lane": "instagram",
                "keyword": inputs.get("keyword"),
                "market": inputs.get("market", "MX"),
            }

    if name == "score_supply_gap":
        try:
            result = harness.score_supply_gap(run_id=run_id, runs_root=runs_root)
            return {
                "artifact": f"artifacts/supply_gap_scores.json",
                "tier_A_count": result["metadata"]["tier_A_count"],
                "tier_B_count": result["metadata"]["tier_B_count"],
                "top_opportunities": result["gap_opportunities"][:5],
            }
        except Exception as exc:
            return {"error": str(exc), "tool": "score_supply_gap"}

    if name == "fetch_pinterest_lane":
        try:
            pack = harness.fetch_pinterest_lane(
                run_id=run_id,
                keyword=inputs["keyword"],
                market=inputs.get("market", "MX"),
                runs_root=runs_root,
            )
            return _summarise_evidence_pack(pack.to_dict())
        except Exception as exc:
            return {
                "error": str(exc),
                "lane": "pinterest",
                "keyword": inputs.get("keyword"),
                "market": inputs.get("market", "MX"),
            }

    return {"error": f"Unknown tool: {name}"}


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

def run_agent(run_id: str, settings: Settings, repo_root: Path) -> str:
    """Run the full research pipeline as an agentic loop.

    The agent reads the brief and existing artifacts, fetches evidence from
    lanes, synthesises artifacts using micro-skill guidance, and writes the
    final catalog. Returns a concise findings summary.

    Args:
        run_id:     Run directory name under runs/.
        settings:   Loaded Settings (must include ANTHROPIC_API_KEY).
        repo_root:  Repository root (contains micro-skills/, orchestration.md, runs/).

    Raises:
        ImportError: if the anthropic package is not installed.
        ValueError:  if ANTHROPIC_API_KEY is not configured.
        FileNotFoundError: if the run directory does not exist.
    """
    if not _ANTHROPIC_AVAILABLE:
        raise ImportError(
            "The 'anthropic' package is required. Install with: pip install anthropic"
        )
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured.")

    runs_root = repo_root / "runs"
    run_dir = runs_root / run_id
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    brief = (run_dir / "raw_brief.md").read_text()

    client = _anthropic.Anthropic(api_key=settings.anthropic_api_key)
    harness = Harness(settings=settings, repo_root=repo_root)
    system = _build_system_prompt(repo_root)

    messages: List[Dict[str, Any]] = [
        {
            "role": "user",
            "content": (
                f"Run the full research pipeline for run_id '{run_id}'.\n\n"
                f"Raw brief:\n{brief}\n\n"
                "Start by listing existing artifacts, then read the client_profile "
                "and lane_plan, decide which lanes to fetch, collect evidence, "
                "synthesise artifacts following the skill guidance in your context, "
                "and produce the final_catalog artifact."
            ),
        }
    ]

    for iteration in range(MAX_ITERATIONS):
        # Retry on rate limit with exponential backoff (up to 3 attempts).
        for attempt in range(3):
            try:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    thinking={"type": "adaptive"},
                    system=system,
                    tools=TOOLS,
                    messages=messages,
                )
                break
            except Exception as exc:
                if "rate_limit" in str(exc).lower() and attempt < 2:
                    wait = 60 * (attempt + 1)
                    print(f"[agent] rate limit hit, waiting {wait}s (attempt {attempt + 1}/3)...")
                    time.sleep(wait)
                else:
                    raise

        # Append the full assistant content (preserves tool_use and thinking blocks).
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            final_text = next(
                (block.text for block in response.content if block.type == "text"),
                "(agent completed with no text summary)",
            )
            return final_text

        if response.stop_reason != "tool_use":
            return f"Unexpected stop_reason: {response.stop_reason}"

        # Execute all tool calls in this turn and collect results.
        tool_results: List[Dict[str, Any]] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = _execute_tool(block.name, block.input, harness, runs_root)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                }
            )

        messages.append({"role": "user", "content": tool_results})

    return f"Agent reached max iterations ({MAX_ITERATIONS}) without completing."
