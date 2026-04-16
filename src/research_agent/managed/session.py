"""Run a managed agent session from a research brief.

Usage:
    research-agent managed-run --input examples/my_brief.json --repo-root .

The brief JSON is embedded in the user message. API keys from .env are
included so the container agent can write /workspace/.env before running
any CLI commands.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# User message builder
# ---------------------------------------------------------------------------

def build_user_message(run_id: str, brief_json: dict, env_vars: dict[str, str]) -> str:
    """Build the first user message for the session.

    Includes:
    - [ENV] block: API keys the agent writes to /workspace/.env
    - [BRIEF] block: the JSON brief the agent uses to initialise the run
    - Task instruction
    """
    env_block = "\n".join(f"{k}={v}" for k, v in env_vars.items() if v)
    brief_block = json.dumps(brief_json, indent=2, ensure_ascii=False)

    return (
        f"[ENV — write these to /workspace/.env before running any commands]\n"
        f"{env_block}\n\n"
        f"[BRIEF — write this to /tmp/brief.json then run init-run]\n"
        f"{brief_block}\n\n"
        f"Run the full research pipeline for run_id '{run_id}'.\n\n"
        f"Steps:\n"
        f"1. Install the research-agent package via pip (see setup instructions in system prompt)\n"
        f"2. Write the [ENV] keys to /workspace/.env exactly as shown\n"
        f"3. Write the [BRIEF] JSON to /tmp/brief.json\n"
        f"4. Run: research-agent init-run --input /tmp/brief.json --repo-root /workspace\n"
        f"5. Follow the orchestration rules in your context to collect evidence, "
        f"score supply gaps, synthesise artifacts, and write final_catalog.json\n"
        f"6. Output a concise findings summary when done"
    )


# ---------------------------------------------------------------------------
# Session runner
# ---------------------------------------------------------------------------

def run_session(
    client: Any,
    agent_id: str,
    environment_id: str,
    run_id: str,
    brief_json: dict,
    env_vars: dict[str, str],
) -> None:
    """Create a session, stream events, print progress to stdout."""
    session = client.beta.sessions.create(
        agent=agent_id,
        environment_id=environment_id,
        title=f"Research: {run_id}",
    )
    print(f"Session: {session.id}", flush=True)
    print(f"Agent:   {agent_id}", flush=True)
    print("-" * 60, flush=True)

    user_message = build_user_message(run_id, brief_json, env_vars)

    with client.beta.sessions.events.stream(session.id) as stream:
        # Send the task message after the stream is open so no events are missed.
        client.beta.sessions.events.send(
            session.id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": user_message}],
                }
            ],
        )

        for event in stream:
            event_type = getattr(event, "type", None)

            if event_type == "agent.message":
                content = getattr(event, "content", [])
                for block in content:
                    text = getattr(block, "text", None)
                    if text:
                        print(text, end="", flush=True)

            elif event_type == "agent.tool_use":
                tool_name = getattr(event, "name", "?")
                tool_input = getattr(event, "input", {})
                # Print a concise one-liner for each tool call.
                if tool_name == "bash":
                    cmd = str(tool_input.get("command", "")).strip()
                    preview = cmd[:120].replace("\n", " ")
                    print(f"\n[bash] {preview}", flush=True)
                elif tool_name in ("read", "write", "edit"):
                    path = tool_input.get("file_path") or tool_input.get("path", "?")
                    print(f"\n[{tool_name}] {path}", flush=True)
                else:
                    print(f"\n[{tool_name}]", flush=True)

            elif event_type == "session.status_idle":
                print("\n" + "-" * 60, flush=True)
                print("Session complete.", flush=True)
                break

            elif event_type == "session.status_terminated":
                error = getattr(event, "error", None)
                print(f"\n[ERROR] Session terminated: {error}", file=sys.stderr, flush=True)
                break
