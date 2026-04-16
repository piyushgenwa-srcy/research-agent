from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

from .agent import run_agent
from .config import Settings
from .harness import Harness
from .models import RunRequest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research-agent")
    sub = parser.add_subparsers(dest="command", required=True)

    init_run = sub.add_parser("init-run", help="Create initial run artifacts from a JSON request")
    init_run.add_argument("--input", required=True, help="Path to run request JSON")
    init_run.add_argument("--repo-root", default=".", help="Repo root path")
    init_run.add_argument("--env-file", default=".env", help="Environment file path, relative to repo root unless absolute")

    show_env = sub.add_parser("connector-status", help="Show connector configuration status")
    show_env.add_argument("--repo-root", default=".", help="Repo root path")
    show_env.add_argument("--env-file", default=".env", help="Environment file path, relative to repo root unless absolute")

    fetch_amazon = sub.add_parser("fetch-amazon-lane", help="Fetch an Amazon lane evidence pack using Oxylabs")
    fetch_amazon.add_argument("--run-id", required=True, help="Run id under runs/")
    fetch_amazon.add_argument("--query", required=True, help="Amazon search query")
    fetch_amazon.add_argument("--repo-root", default=".", help="Repo root path")
    fetch_amazon.add_argument("--env-file", default=".env", help="Environment file path, relative to repo root unless absolute")

    fetch_tiktok = sub.add_parser("fetch-tiktok-lane", help="Fetch a TikTok lane evidence pack using Ensemble")
    fetch_tiktok.add_argument("--run-id", required=True, help="Run id under runs/")
    fetch_tiktok.add_argument("--keyword", required=True, help="TikTok keyword to search")
    fetch_tiktok.add_argument("--repo-root", default=".", help="Repo root path")
    fetch_tiktok.add_argument("--env-file", default=".env", help="Environment file path, relative to repo root unless absolute")

    fetch_ml = sub.add_parser("fetch-mercadolibre-lane", help="Fetch a MercadoLibre lane evidence pack using Oxylabs")
    fetch_ml.add_argument("--run-id", required=True, help="Run id under runs/")
    fetch_ml.add_argument("--query", required=True, help="MercadoLibre search keyword")
    fetch_ml.add_argument("--market", default="MX", help="ISO market code: MX (default), AR, BR, CO, CL")
    fetch_ml.add_argument("--repo-root", default=".", help="Repo root path")
    fetch_ml.add_argument("--env-file", default=".env", help="Environment file path, relative to repo root unless absolute")

    fetch_tt_vertical = sub.add_parser("fetch-tiktok-vertical", help="Two-pass vertical TikTok collection: breadth + comment depth")
    fetch_tt_vertical.add_argument("--run-id", required=True)
    fetch_tt_vertical.add_argument("--keywords", required=True, help="Comma-separated keyword list")
    fetch_tt_vertical.add_argument("--period", type=int, default=90, help="Days lookback (default 90)")
    fetch_tt_vertical.add_argument("--max-pages", type=int, default=3, help="Max pages per keyword (default 3)")
    fetch_tt_vertical.add_argument("--depth-n", type=int, default=20, help="Top N posts to fetch comments for (default 20)")
    fetch_tt_vertical.add_argument("--repo-root", default=".")
    fetch_tt_vertical.add_argument("--env-file", default=".env")

    fetch_pinterest = sub.add_parser("fetch-pinterest-lane", help="Fetch a Pinterest lane evidence pack via SerpAPI Google site:pinterest.com search")
    fetch_pinterest.add_argument("--run-id", required=True, help="Run id under runs/")
    fetch_pinterest.add_argument("--keyword", required=True, help="Pinterest keyword to search")
    fetch_pinterest.add_argument("--market", default="MX", help="ISO market code: MX (default), AR, BR, CO, CL")
    fetch_pinterest.add_argument("--repo-root", default=".", help="Repo root path")
    fetch_pinterest.add_argument("--env-file", default=".env", help="Environment file path, relative to repo root unless absolute")

    fetch_ig = sub.add_parser("fetch-instagram-lane", help="Fetch an Instagram lane evidence pack via SerpAPI Google search")
    fetch_ig.add_argument("--run-id", required=True, help="Run id under runs/")
    fetch_ig.add_argument("--keyword", required=True, help="Instagram keyword to search")
    fetch_ig.add_argument("--market", default="MX", help="ISO market code: MX (default), AR, BR, CO, CL")
    fetch_ig.add_argument("--repo-root", default=".", help="Repo root path")
    fetch_ig.add_argument("--env-file", default=".env", help="Environment file path, relative to repo root unless absolute")

    run_agent_cmd = sub.add_parser("run-agent", help="Run the full research pipeline as an agentic loop powered by Claude")
    run_agent_cmd.add_argument("--run-id", required=True, help="Run id under runs/ (must have raw_brief.md, client_profile.json, lane_plan.json)")
    run_agent_cmd.add_argument("--repo-root", default=".", help="Repo root path")
    run_agent_cmd.add_argument("--env-file", default=".env", help="Environment file path, relative to repo root unless absolute")

    return parser


def resolve_env_file(repo_root: Path, env_file: str) -> Path:
    env_path = Path(env_file)
    if env_path.is_absolute():
        return env_path
    return repo_root / env_file


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    env_file = resolve_env_file(repo_root, args.env_file)
    settings = Settings.load(env_file)

    if args.command == "connector-status":
        print(json.dumps(settings.connector_status(), indent=2))
        return 0

    if args.command == "init-run":
        input_path = Path(args.input).resolve()
        request = RunRequest.from_json(input_path.read_text())
        harness = Harness(settings=settings, repo_root=repo_root)
        state = harness.create_run(request)
        result = {
            "run_id": state.request.run_id,
            "connector_status": state.connector_status,
            "gaps": state.gaps,
            "artifacts": [
                str((repo_root / "runs" / state.request.run_id / "run_request.json")),
                str((repo_root / "runs" / state.request.run_id / "client_profile.json")),
                str((repo_root / "runs" / state.request.run_id / "lane_plan.json")),
            ],
        }
        if state.market_assortment_context is not None:
            result["artifacts"].append(str(repo_root / "runs" / state.request.run_id / "market_assortment_context.json"))
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "fetch-amazon-lane":
        harness = Harness(settings=settings, repo_root=repo_root)
        evidence_pack = harness.fetch_amazon_lane(run_id=args.run_id, query=args.query)
        print(json.dumps(evidence_pack.to_dict(), indent=2))
        return 0

    if args.command == "fetch-tiktok-lane":
        harness = Harness(settings=settings, repo_root=repo_root)
        evidence_pack = harness.fetch_tiktok_lane(run_id=args.run_id, keyword=args.keyword)
        print(json.dumps(evidence_pack.to_dict(), indent=2))
        return 0

    if args.command == "fetch-mercadolibre-lane":
        harness = Harness(settings=settings, repo_root=repo_root)
        evidence_pack = harness.fetch_mercadolibre_lane(
            run_id=args.run_id,
            query=args.query,
            market=args.market,
        )
        print(json.dumps(evidence_pack.to_dict(), indent=2))
        return 0

    if args.command == "fetch-tiktok-vertical":
        harness = Harness(settings=settings, repo_root=repo_root)
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
        result = harness.fetch_tiktok_vertical(
            run_id=args.run_id,
            keywords=keywords,
            period=args.period,
            max_pages_per_keyword=args.max_pages,
            depth_top_n=args.depth_n,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "fetch-pinterest-lane":
        harness = Harness(settings=settings, repo_root=repo_root)
        evidence_pack = harness.fetch_pinterest_lane(
            run_id=args.run_id,
            keyword=args.keyword,
            market=args.market,
        )
        print(json.dumps(evidence_pack.to_dict(), indent=2))
        return 0

    if args.command == "fetch-instagram-lane":
        harness = Harness(settings=settings, repo_root=repo_root)
        evidence_pack = harness.fetch_instagram_lane(
            run_id=args.run_id,
            keyword=args.keyword,
            market=args.market,
        )
        print(json.dumps(evidence_pack.to_dict(), indent=2))
        return 0

    if args.command == "run-agent":
        summary = run_agent(args.run_id, settings, repo_root)
        print(summary)
        return 0

    parser.print_help(sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
