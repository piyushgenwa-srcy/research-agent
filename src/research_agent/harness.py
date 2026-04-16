from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse
import json

from .artifact_io import write_json, write_text
from .config import Settings
from .connectors.ensemble import EnsembleClient
from .connectors.oxylabs import ML_MARKET_DOMAIN, OxylabsClient
from .connectors.serpapi import SerpApiClient
from .extractors import build_amazon_evidence_pack, build_instagram_evidence_pack, build_mercadolibre_evidence_pack, build_pinterest_evidence_pack, build_tiktok_evidence_pack
from .supply_gap import score_supply_gap
from .tiktok_vertical import collect_vertical_signal
from .models import (
    BuyerProfile,
    CapabilityHints,
    CategorySummary,
    ClientProfile,
    GapHypothesis,
    LanePlan,
    LaneTarget,
    MarketAssortmentContext,
    MarketContextSummary,
    RetailerSummary,
    RunRequest,
    RunState,
    SearchPriorities,
    LaneEvidencePack,
)
from .validators import validate_client_profile, validate_market_context


PHARMACY_KEYWORDS = ("farmacias", "dermo", "skin", "cuidado")
SPECIALIST_KEYWORDS = ("sally", "beauty", "cosmetic", "maquillaje", "unas", "accesorios")


def infer_retailer_name(url: str) -> str:
    last = urlparse(url).path.strip("/").split("/")[-2 if "/" in urlparse(url).path.strip("/") else -1]
    return last.split("-", 1)[-1].replace("-", " ").title() if last else "Unknown Retailer"


def infer_category(url: str) -> str:
    tail = urlparse(url).path.strip("/").split("/")[-1] if urlparse(url).path.strip("/") else "storefront root"
    return tail.replace("-", " ")


def infer_archetype(categories: List[str], retailer_name: str) -> str:
    name = retailer_name.lower()
    joined = " ".join(categories).lower()
    if "sally" in name or any(word in joined for word in SPECIALIST_KEYWORDS):
        return "specialist beauty"
    if "farmacia" in name or any(word in joined for word in PHARMACY_KEYWORDS):
        return "pharmacy-led beauty"
    return "generalist or brand-led beauty"


@dataclass
class Harness:
    settings: Settings
    repo_root: Path

    def create_run(self, request: RunRequest, runs_root: Path | None = None) -> RunState:
        state = RunState(request=request, connector_status=self.settings.connector_status())
        if runs_root is None:
            runs_root = self.repo_root / "runs"
        run_dir = runs_root / request.run_id
        write_text(run_dir / "raw_brief.md", request.raw_brief.strip() + "\n")
        write_json(run_dir / "run_request.json", request.to_dict())

        if request.retailer_urls:
            state.market_assortment_context = self._build_market_context(request)
            write_json(run_dir / "market_assortment_context.json", state.market_assortment_context)
            state.gaps.extend(validate_market_context(state.market_assortment_context))

        state.client_profile = self._build_client_profile(request, state.market_assortment_context)
        write_json(run_dir / "client_profile.json", state.client_profile)
        state.gaps.extend(validate_client_profile(state.client_profile))

        state.lane_plan = self._build_lane_plan(request, state.market_assortment_context)
        write_json(run_dir / "lane_plan.json", state.lane_plan)

        gap_lines = [
            "# Run Gaps",
            "",
            "## Connector Status",
        ]
        for name, ok in state.connector_status.items():
            gap_lines.append(f"- {name}: {'configured' if ok else 'missing or incomplete'}")
        if state.gaps:
            gap_lines.extend(["", "## Validation / Run Gaps"])
            gap_lines.extend([f"- {gap}" for gap in state.gaps])
        write_text(run_dir / "run_gaps.md", "\n".join(gap_lines) + "\n")
        return state

    def fetch_amazon_lane(self, run_id: str, query: str, runs_root: Path | None = None) -> LaneEvidencePack:
        if not self.settings.oxylab_username or not self.settings.oxylab_password:
            raise ValueError("Oxylabs credentials are not configured.")
        if runs_root is None:
            runs_root = self.repo_root / "runs"
        run_dir = runs_root / run_id
        request = RunRequest.from_json((run_dir / "run_request.json").read_text())
        state = self.create_run(request, runs_root=runs_root) if not (run_dir / "client_profile.json").exists() else None
        if state is not None:
            client_profile = state.client_profile
            lane_plan = state.lane_plan
        else:
            client_profile = ClientProfile.from_dict(json.loads((run_dir / "client_profile.json").read_text()))
            lane_plan = LanePlan.from_dict(json.loads((run_dir / "lane_plan.json").read_text()))
        client = OxylabsClient(username=self.settings.oxylab_username, password=self.settings.oxylab_password)
        response = client.amazon_search(query)
        raw_dir = run_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        safe_query = query.lower().replace(" ", "-")
        raw_path = raw_dir / f"amazon-{safe_query}.json"
        write_json(raw_path, response)
        evidence_pack = build_amazon_evidence_pack(
            response=response,
            query=query,
            lane_plan=lane_plan,
            client_profile=client_profile,
            raw_response_path=str(raw_path),
        )
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        write_json(artifacts_dir / f"lane_evidence_pack_amazon_{safe_query}.json", evidence_pack)
        return evidence_pack

    def fetch_tiktok_lane(self, run_id: str, keyword: str, runs_root: Path | None = None) -> LaneEvidencePack:
        if not self.settings.ensemble_api_key:
            raise ValueError("Ensemble API key is not configured.")
        if runs_root is None:
            runs_root = self.repo_root / "runs"
        run_dir = runs_root / run_id
        client_profile = ClientProfile.from_dict(json.loads((run_dir / "client_profile.json").read_text()))
        lane_plan = LanePlan.from_dict(json.loads((run_dir / "lane_plan.json").read_text()))
        client = EnsembleClient(api_key=self.settings.ensemble_api_key)
        response = client.tiktok_keyword_search(keyword)
        raw_dir = run_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        safe_keyword = keyword.lower().replace(" ", "-")
        raw_path = raw_dir / f"tiktok-{safe_keyword}.json"
        write_json(raw_path, response)
        evidence_pack = build_tiktok_evidence_pack(
            response=response,
            keyword=keyword,
            lane_plan=lane_plan,
            client_profile=client_profile,
            raw_response_path=str(raw_path),
        )
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        write_json(artifacts_dir / f"lane_evidence_pack_tiktok_{safe_keyword}.json", evidence_pack)
        return evidence_pack

    def fetch_mercadolibre_lane(
        self,
        run_id: str,
        query: str,
        market: str = "MX",
        runs_root: Path | None = None,
    ) -> LaneEvidencePack:
        """Fetch a MercadoLibre lane evidence pack via Oxylabs universal scraper.

        Args:
            run_id: Existing run directory under runs/.
            query:  Search keyword to scrape on MercadoLibre.
            market: ISO market code (MX, AR, BR, CO, CL). Determines the domain.
        """
        if not self.settings.oxylab_username or not self.settings.oxylab_password:
            raise ValueError("Oxylabs credentials are not configured.")
        if runs_root is None:
            runs_root = self.repo_root / "runs"
        run_dir = runs_root / run_id
        client_profile = ClientProfile.from_dict(json.loads((run_dir / "client_profile.json").read_text()))
        lane_plan = LanePlan.from_dict(json.loads((run_dir / "lane_plan.json").read_text()))
        domain = ML_MARKET_DOMAIN.get(market.upper(), "com.mx")
        client = OxylabsClient(username=self.settings.oxylab_username, password=self.settings.oxylab_password)
        response = client.mercadolibre_search(query, domain=domain)
        raw_dir = run_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        safe_query = query.lower().replace(" ", "-")
        raw_path = raw_dir / f"mercadolibre-{market.lower()}-{safe_query}.json"
        write_json(raw_path, response)
        evidence_pack = build_mercadolibre_evidence_pack(
            response=response,
            query=query,
            lane_plan=lane_plan,
            client_profile=client_profile,
            raw_response_path=str(raw_path),
            domain=domain,
        )
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        write_json(artifacts_dir / f"lane_evidence_pack_mercadolibre-{market.lower()}_{safe_query}.json", evidence_pack)
        return evidence_pack

    def fetch_tiktok_vertical(
        self,
        run_id: str,
        keywords: List[str],
        period: int = 90,
        max_pages_per_keyword: int = 3,
        max_hashtag_expansion: int = 5,
        depth_top_n: int = 20,
        runs_root: Path | None = None,
    ) -> Dict[str, Any]:
        """Two-pass vertical TikTok collection: breadth (multi-keyword+hashtag) + depth (comments).

        Writes artifacts/tiktok_vertical_signal.json and raw/tiktok-vertical-*.json.
        Returns a concise summary dict for the agent.
        """
        if not self.settings.ensemble_api_key:
            raise ValueError("Ensemble API key is not configured.")
        if runs_root is None:
            runs_root = self.repo_root / "runs"
        run_dir = runs_root / run_id
        client = EnsembleClient(api_key=self.settings.ensemble_api_key)
        signal = collect_vertical_signal(
            client,
            keywords=keywords,
            period=period,
            max_pages_per_keyword=max_pages_per_keyword,
            max_hashtag_expansion=max_hashtag_expansion,
            depth_top_n=depth_top_n,
            anthropic_api_key=self.settings.anthropic_api_key or None,
        )
        raw_dir = run_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        write_json(raw_dir / "tiktok-vertical.json", signal)
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = artifacts_dir / "tiktok_vertical_signal.json"
        write_json(artifact_path, signal)
        return {
            "artifact": str(artifact_path),
            "total_posts": signal["total_posts_collected"],
            "keywords_searched": signal["keywords_searched"],
            "hashtags_expanded": signal["hashtags_expanded"],
            "deep_posts_analysed": len(signal["deep_posts"]),
            "top_hashtags": list(signal["hashtag_frequency"].keys())[:15],
            "cohort_clusters": [
                {
                    "top_hashtags": c["top_hashtags"][:5],
                    "post_count": c["post_count"],
                    "avg_save_to_view_ratio": c["avg_save_to_view_ratio"],
                }
                for c in signal.get("cohort_clusters", [])[:5]
            ],
            "trend_velocity": {
                "avg_velocity": signal.get("trend_velocity", {}).get("avg_velocity"),
                "top_accelerating": signal.get("trend_velocity", {}).get("top_accelerating", []),
            },
            "top_by_save_to_view": [
                {
                    "desc": p["desc"][:80],
                    "views": p["views"],
                    "saves": p["saves"],
                    "save_to_view_ratio": p["save_to_view_ratio"],
                    "url": p["url"],
                }
                for p in signal["top_by_save_to_view_ratio"][:5]
            ],
            "demand_signals": signal["demand_signals"],
        }

    def fetch_instagram_lane(
        self,
        run_id: str,
        keyword: str,
        market: str = "MX",
        runs_root: Path | None = None,
    ) -> LaneEvidencePack:
        """Fetch Instagram trend signals via SerpAPI Google site:instagram.com search."""
        if not self.settings.serp_api_key:
            raise ValueError("SerpAPI key is not configured.")
        if runs_root is None:
            runs_root = self.repo_root / "runs"
        run_dir = runs_root / run_id
        client_profile = ClientProfile.from_dict(json.loads((run_dir / "client_profile.json").read_text()))
        lane_plan = LanePlan.from_dict(json.loads((run_dir / "lane_plan.json").read_text()))
        client = SerpApiClient(api_key=self.settings.serp_api_key)
        response = client.instagram_keyword_search(keyword, market=market)
        raw_dir = run_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        safe_keyword = keyword.lower().replace(" ", "-")
        raw_path = raw_dir / f"instagram-{market.lower()}-{safe_keyword}.json"
        write_json(raw_path, response)
        evidence_pack = build_instagram_evidence_pack(
            response=response,
            keyword=keyword,
            lane_plan=lane_plan,
            client_profile=client_profile,
            raw_response_path=str(raw_path),
        )
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        write_json(artifacts_dir / f"lane_evidence_pack_instagram-{market.lower()}_{safe_keyword}.json", evidence_pack)
        return evidence_pack

    def score_supply_gap(
        self,
        run_id: str,
        runs_root: Path | None = None,
    ) -> Dict[str, Any]:
        """Score supply-demand gap using tiktok_vertical_signal + ML evidence packs.

        Reads artifacts/tiktok_vertical_signal.json and all
        artifacts/lane_evidence_pack_mercadolibre-*.json from the run directory.
        Writes artifacts/supply_gap_scores.json and returns the result.
        """
        if runs_root is None:
            runs_root = self.repo_root / "runs"
        run_dir = runs_root / run_id
        artifacts_dir = run_dir / "artifacts"

        tiktok_path = artifacts_dir / "tiktok_vertical_signal.json"
        if not tiktok_path.exists():
            raise FileNotFoundError(
                "tiktok_vertical_signal.json not found — run fetch_tiktok_vertical first."
            )
        import json as _json
        tiktok_signal = _json.loads(tiktok_path.read_text())

        ml_packs: List[Dict[str, Any]] = []
        for ml_path in sorted(artifacts_dir.glob("lane_evidence_pack_mercadolibre-*.json")):
            try:
                ml_packs.append(_json.loads(ml_path.read_text()))
            except Exception:
                pass

        result = score_supply_gap(tiktok_signal, ml_packs)
        write_json(artifacts_dir / "supply_gap_scores.json", result)
        return result

    def fetch_pinterest_lane(
        self,
        run_id: str,
        keyword: str,
        market: str = "MX",
        runs_root: Path | None = None,
    ) -> LaneEvidencePack:
        """Fetch Pinterest visual trend signals via SerpAPI Google site:pinterest.com search.

        Strong signal for 28-45 cohort, aspirational aesthetics, and early-stage trends
        that precede TikTok virality.
        """
        if not self.settings.serp_api_key:
            raise ValueError("SerpAPI key is not configured.")
        if runs_root is None:
            runs_root = self.repo_root / "runs"
        run_dir = runs_root / run_id
        client_profile = ClientProfile.from_dict(json.loads((run_dir / "client_profile.json").read_text()))
        lane_plan = LanePlan.from_dict(json.loads((run_dir / "lane_plan.json").read_text()))
        client = SerpApiClient(api_key=self.settings.serp_api_key)
        response = client.pinterest_keyword_search(keyword, market=market)
        raw_dir = run_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        safe_keyword = keyword.lower().replace(" ", "-")
        raw_path = raw_dir / f"pinterest-{market.lower()}-{safe_keyword}.json"
        write_json(raw_path, response)
        evidence_pack = build_pinterest_evidence_pack(
            response=response,
            keyword=keyword,
            lane_plan=lane_plan,
            client_profile=client_profile,
            raw_response_path=str(raw_path),
        )
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        write_json(artifacts_dir / f"lane_evidence_pack_pinterest-{market.lower()}_{safe_keyword}.json", evidence_pack)
        return evidence_pack

    def _build_market_context(self, request: RunRequest) -> MarketAssortmentContext:
        grouped: Dict[str, List[str]] = {}
        for url in request.retailer_urls:
            grouped.setdefault(infer_retailer_name(url), []).append(url)

        retailers: List[RetailerSummary] = []
        benchmark_retailers: List[str] = []
        observed_subcategories: List[str] = []
        for retailer_name, urls in grouped.items():
            categories = sorted({infer_category(url) for url in urls})
            observed_subcategories.extend(categories)
            archetype = infer_archetype(categories, retailer_name)
            benchmark_retailers.append(retailer_name)
            retailers.append(
                RetailerSummary(
                    retailer_name=retailer_name,
                    store_urls=urls,
                    observed_categories=categories,
                    assortment_profile=f"{archetype} coverage inferred from supplied category/store URLs.",
                    retailer_archetype=archetype,
                    coverage_notes="Built from retailer/category URLs only; product-level assortment depth still needs a scraper or manual fetch.",
                )
            )

        category_summary = [
            CategorySummary(
                category=request.categories[0] if request.categories else "unknown",
                observed_subcategories=sorted(set(observed_subcategories)),
                saturated_themes=[
                    "routine care categories with repeated pharmacy and specialist presence",
                    "conventional staples indicated by repeated category coverage",
                ],
                undercovered_hypotheses=[
                    "travel-size impulse formats",
                    "quick-commerce basket builders",
                    "beauty accessories outside specialist stores",
                ],
                market_note="Current context is inferred from retailer/category coverage, not fetched product-level inventory.",
            )
        ]
        gap_hypotheses = [
            GapHypothesis(
                gap_type="retailer_gap",
                category=request.categories[0] if request.categories else "unknown",
                gap_name="specialist-only accessory depth",
                evidence="Specialist beauty retailers appear more likely than pharmacy-led stores to carry accessories and non-routine beauty adjacencies.",
                confidence="MEDIUM",
            )
        ]
        return MarketAssortmentContext(
            platform=request.platform,
            markets=request.markets,
            focus_categories=request.categories[:1] or ["unknown"],
            retailers=retailers,
            category_summary=category_summary,
            gap_hypotheses=gap_hypotheses,
            search_priorities=SearchPriorities(
                prioritize=["beauty accessories", "travel-size formats", "basket builders"],
                deprioritize=["commodity staples", "routine treatment products"],
                benchmark_retailers=benchmark_retailers,
            ),
            warnings=[
                "market context inferred from URLs and category labels only",
                "connector-backed retailer scraping is not implemented yet",
            ],
        )

    def _build_client_profile(
        self,
        request: RunRequest,
        market_context: MarketAssortmentContext | None,
    ) -> ClientProfile:
        motivation = "impulse" if request.platform.lower() == "rappi" else "browsing"
        delivery = "minutes" if request.platform.lower() == "rappi" else "flexible"
        capability_hints = CapabilityHints(
            prioritize_lanes=["tiktok", "amazon"] if request.platform.lower() == "rappi" else ["tiktok"],
            use_market_assortment_context=market_context is not None,
            needs_sku_mapping=True,
            needs_sentiment_analysis=request.use_case in {"private_label", "white_label"},
        )
        market_summary = MarketContextSummary()
        if market_context is not None:
            market_summary = MarketContextSummary(
                benchmark_retailers=market_context.search_priorities.benchmark_retailers,
                observed_coverage_notes=[c.market_note for c in market_context.category_summary],
                gap_priority_areas=market_context.search_priorities.prioritize,
                deprioritized_areas=market_context.search_priorities.deprioritize,
            )
        trend_definition = (
            "Products currently trending in external quick-commerce or adjacent consumer channels that are still underpenetrated in the "
            f"target market for {request.client_name}, plus operational products that improve merchant, warehouse, or delivery workflows."
        )
        return ClientProfile(
            platform=request.platform,
            client_name=request.client_name,
            trend_definition=trend_definition,
            buyer_profile=BuyerProfile(
                description=f"{request.client_name} buyer and operator frame inferred from brief.",
                motivation=motivation,
                delivery_expectation=delivery,
            ),
            markets=request.markets,
            categories=request.categories,
            price_bracket=request.price_bracket,
            output_mode=request.output_mode,
            benchmark_sources=request.benchmark_sources,
            market_context=market_summary,
            use_case=request.use_case,
            moq=request.moq,
            min_products=request.min_products,
            max_products=request.max_products,
            ship_to=request.ship_to,
            capability_hints=capability_hints,
            inference_notes=[
                "client profile created by the executable harness using request fields and platform defaults",
                "trend definition is scaffolding and should be refined by an LLM-guided pass later",
            ],
        )

    def _build_lane_plan(
        self,
        request: RunRequest,
        market_context: MarketAssortmentContext | None,
    ) -> LanePlan:
        prioritize = market_context.search_priorities.prioritize if market_context else ["compact formats", "novelty-led quick-commerce items"]
        deprioritize = market_context.search_priorities.deprioritize if market_context else ["commodity staples"]
        lanes = [
            LaneTarget(
                lane="tiktok",
                priority="high",
                search_objective=(
                    f"Collect {request.categories[0] if request.categories else 'in-scope'} signals that fit {request.platform} quick-commerce behavior "
                    "and bias toward compact, impulse-friendly formats."
                ),
                prioritized_hypotheses=prioritize,
                in_scope_signals=[
                    "repeat creator mentions",
                    "clear compact product use case",
                    "fast basket-builder potential",
                ],
                deprioritized_signals=deprioritize,
                artifact_goal="lane_evidence_pack",
            ),
            LaneTarget(
                lane="amazon",
                priority="high",
                search_objective=(
                    "Collect generic product-format evidence, packaging cues, and early-mover ranking signals that make sourcing decisions more concrete."
                ),
                prioritized_hypotheses=prioritize,
                in_scope_signals=[
                    "clear generic product format",
                    "compact packaging",
                    "lower-review-count items ranking well enough to merit review",
                ],
                deprioritized_signals=deprioritize,
                artifact_goal="lane_evidence_pack",
            ),
        ]
        return LanePlan(
            run_id=request.run_id,
            focus_category=request.categories[0] if request.categories else "unknown",
            lanes=lanes,
        )
