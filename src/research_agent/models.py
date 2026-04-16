from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Dict, List, Optional
import json


def to_serializable(value: Any) -> Any:
    if is_dataclass(value):
        return {k: to_serializable(v) for k, v in asdict(value).items()}
    if isinstance(value, list):
        return [to_serializable(v) for v in value]
    if isinstance(value, dict):
        return {k: to_serializable(v) for k, v in value.items()}
    return value


@dataclass
class BuyerProfile:
    description: str
    motivation: str
    delivery_expectation: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuyerProfile":
        return cls(**data)


@dataclass
class CapabilityHints:
    prioritize_lanes: List[str] = field(default_factory=list)
    use_market_assortment_context: bool = False
    needs_sku_mapping: bool = False
    needs_sentiment_analysis: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityHints":
        return cls(**data)


@dataclass
class MarketContextSummary:
    benchmark_retailers: List[str] = field(default_factory=list)
    observed_coverage_notes: List[str] = field(default_factory=list)
    gap_priority_areas: List[str] = field(default_factory=list)
    deprioritized_areas: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MarketContextSummary":
        return cls(**data)


@dataclass
class ClientProfile:
    platform: str
    client_name: str
    trend_definition: str
    buyer_profile: BuyerProfile
    markets: List[str]
    categories: List[str]
    price_bracket: str
    output_mode: str
    benchmark_sources: List[str]
    market_context: MarketContextSummary
    use_case: str
    moq: int
    min_products: int
    max_products: int
    ship_to: str
    capability_hints: CapabilityHints
    inference_notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return to_serializable(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientProfile":
        return cls(
            platform=data["platform"],
            client_name=data["client_name"],
            trend_definition=data["trend_definition"],
            buyer_profile=BuyerProfile.from_dict(data["buyer_profile"]),
            markets=data["markets"],
            categories=data["categories"],
            price_bracket=data["price_bracket"],
            output_mode=data["output_mode"],
            benchmark_sources=data["benchmark_sources"],
            market_context=MarketContextSummary.from_dict(data["market_context"]),
            use_case=data["use_case"],
            moq=data["moq"],
            min_products=data["min_products"],
            max_products=data["max_products"],
            ship_to=data["ship_to"],
            capability_hints=CapabilityHints.from_dict(data["capability_hints"]),
            inference_notes=data.get("inference_notes", []),
        )


@dataclass
class RetailerInput:
    url: str
    category_hint: Optional[str] = None


@dataclass
class RetailerSummary:
    retailer_name: str
    store_urls: List[str]
    observed_categories: List[str]
    assortment_profile: str
    retailer_archetype: str
    coverage_notes: str


@dataclass
class CategorySummary:
    category: str
    observed_subcategories: List[str]
    saturated_themes: List[str]
    undercovered_hypotheses: List[str]
    market_note: str


@dataclass
class GapHypothesis:
    gap_type: str
    category: str
    gap_name: str
    evidence: str
    confidence: str


@dataclass
class SearchPriorities:
    prioritize: List[str]
    deprioritize: List[str]
    benchmark_retailers: List[str]


@dataclass
class MarketAssortmentContext:
    platform: str
    markets: List[str]
    focus_categories: List[str]
    retailers: List[RetailerSummary]
    category_summary: List[CategorySummary]
    gap_hypotheses: List[GapHypothesis]
    search_priorities: SearchPriorities
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return to_serializable(self)


@dataclass
class LaneTarget:
    lane: str
    priority: str
    search_objective: str
    prioritized_hypotheses: List[str]
    in_scope_signals: List[str]
    deprioritized_signals: List[str]
    artifact_goal: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LaneTarget":
        return cls(**data)


@dataclass
class LanePlan:
    run_id: str
    focus_category: str
    lanes: List[LaneTarget]

    def to_dict(self) -> Dict[str, Any]:
        return to_serializable(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LanePlan":
        return cls(
            run_id=data["run_id"],
            focus_category=data["focus_category"],
            lanes=[LaneTarget.from_dict(item) for item in data["lanes"]],
        )


@dataclass
class EvidenceMetrics:
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    saves: Optional[int] = None
    rank: Optional[int] = None
    review_count: Optional[int] = None
    rating: Optional[float] = None
    price: Optional[float] = None


@dataclass
class EvidenceItem:
    source_id: str
    source_type: str
    title_or_caption: str
    creator_or_seller: Optional[str]
    published_at: Optional[str]
    metrics: EvidenceMetrics
    is_original_signal: bool
    repost_suspected: bool
    evidence_note: str


@dataclass
class EvidenceCandidate:
    source_product_label: str
    normalized_product_name: str
    generic_format_note: str
    evidence_items: List[EvidenceItem]
    evidence_count: int
    naming_uncertainty: List[str]
    data_quality_flags: List[str]
    collection_note: str


@dataclass
class ExcludedItem:
    source_product_label: str
    reason: str


@dataclass
class LaneEvidencePack:
    lane: str
    search_objective: str
    client_scope: Dict[str, Any]
    candidates: List[EvidenceCandidate]
    extraction_warnings: List[str]
    excluded_items: List[ExcludedItem]
    raw_response_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return to_serializable(self)


@dataclass
class RunRequest:
    run_id: str
    client_name: str
    platform: str
    raw_brief: str
    markets: List[str]
    ship_to: str
    categories: List[str]
    benchmark_sources: List[str]
    retailer_urls: List[str] = field(default_factory=list)
    price_bracket: str = "mid-market"
    output_mode: str = "catalog"
    use_case: str = "sourcing"
    moq: int = 50
    min_products: int = 5
    max_products: int = 10

    @classmethod
    def from_json(cls, text: str) -> "RunRequest":
        data = json.loads(text)
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        return to_serializable(self)


@dataclass
class RunState:
    request: RunRequest
    connector_status: Dict[str, bool]
    market_assortment_context: Optional[MarketAssortmentContext] = None
    client_profile: Optional[ClientProfile] = None
    lane_plan: Optional[LanePlan] = None
    lane_evidence_packs: Dict[str, LaneEvidencePack] = field(default_factory=dict)
    gaps: List[str] = field(default_factory=list)
