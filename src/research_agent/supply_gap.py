"""Supply-gap scorer: cross-references TikTok demand signal with MercadoLibre supply.

Computes a gap score per cohort cluster:
    demand_score  = normalised(total_posts × avg_save_to_view_ratio)
    supply_score  = normalised(ML listing count for matched query)
    gap_score     = demand_score / (supply_score + epsilon)

Inputs
------
tiktok_signal : dict
    Output of ``collect_vertical_signal`` — must contain ``cohort_clusters``
    and ``hashtag_frequency``.
ml_evidence_packs : List[dict]
    One or more ``lane_evidence_pack.to_dict()`` outputs from
    ``fetch_mercadolibre_lane`` (lane == "mercadolibre").

Output
------
A ranked list of gap opportunities with confidence tier.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

_EPSILON = 1e-6

# Confidence tiers based on gap_score percentile
_TIER_A = 0.7    # top 30% — strong gap
_TIER_B = 0.4    # 40-70% — moderate gap
# below _TIER_B  → weak gap (supply meets demand)


def _normalise(values: List[float]) -> List[float]:
    """Min-max normalise a list of floats to [0, 1]. Returns zeros if all same."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def score_supply_gap(
    tiktok_signal: Dict[str, Any],
    ml_evidence_packs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Score supply-demand gap per cohort cluster.

    Args:
        tiktok_signal:     Full output of ``collect_vertical_signal``.
        ml_evidence_packs: List of MercadoLibre evidence pack dicts.

    Returns:
        Dict with ``gap_opportunities`` (ranked list) and ``metadata``.
    """
    clusters = tiktok_signal.get("cohort_clusters", [])
    hashtag_freq = tiktok_signal.get("hashtag_frequency", {})
    total_posts = max(tiktok_signal.get("total_posts_collected", 1), 1)

    # Build ML supply index: query → listing count
    ml_supply: Dict[str, int] = {}
    for pack in ml_evidence_packs:
        if pack.get("lane") != "mercadolibre":
            continue
        query = (pack.get("client_scope") or {}).get("query", "")
        if query:
            ml_supply[query.lower()] = len(pack.get("candidates", []))

    # -------------------------------------------------------------------
    # Build demand vectors per cluster
    # -------------------------------------------------------------------
    cluster_demand_raw: List[float] = []
    for c in clusters:
        # demand proxy: post share × avg STR (save-to-view ratio)
        post_share = c.get("post_count", 0) / total_posts
        avg_str = c.get("avg_save_to_view_ratio", 0.0)
        raw_demand = post_share * avg_str * 1000  # scale up
        cluster_demand_raw.append(raw_demand)

    cluster_demand_norm = _normalise(cluster_demand_raw)

    # -------------------------------------------------------------------
    # Build supply vectors per cluster (match top hashtags → ML queries)
    # -------------------------------------------------------------------
    cluster_supply_raw: List[float] = []
    cluster_ml_match: List[Optional[str]] = []

    for c in clusters:
        top_hashtags = c.get("top_hashtags", [])
        best_match: Optional[str] = None
        best_count = 0
        for ht in top_hashtags[:5]:
            ht_lower = ht.lower()
            for query, count in ml_supply.items():
                # fuzzy match: query contains hashtag or vice versa
                if ht_lower in query or query in ht_lower:
                    if count > best_count:
                        best_count = count
                        best_match = query
        cluster_supply_raw.append(float(best_count))
        cluster_ml_match.append(best_match)

    cluster_supply_norm = _normalise(cluster_supply_raw)

    # -------------------------------------------------------------------
    # Gap scores
    # -------------------------------------------------------------------
    gap_scores_raw: List[float] = []
    for d_norm, s_norm in zip(cluster_demand_norm, cluster_supply_norm):
        gap = d_norm / (s_norm + _EPSILON)
        gap_scores_raw.append(gap)

    gap_scores_norm = _normalise(gap_scores_raw)

    # -------------------------------------------------------------------
    # Build output
    # -------------------------------------------------------------------
    opportunities: List[Dict[str, Any]] = []
    for idx, (c, d_raw, d_norm, s_raw, s_norm, g_norm, ml_q) in enumerate(zip(
        clusters,
        cluster_demand_raw,
        cluster_demand_norm,
        cluster_supply_raw,
        cluster_supply_norm,
        gap_scores_norm,
        cluster_ml_match,
    )):
        if g_norm >= _TIER_A:
            tier = "A"
        elif g_norm >= _TIER_B:
            tier = "B"
        else:
            tier = "C"

        opportunities.append({
            "rank": idx + 1,
            "cohort_hashtags": c.get("top_hashtags", [])[:6],
            "post_count": c.get("post_count", 0),
            "avg_save_to_view_ratio": c.get("avg_save_to_view_ratio", 0.0),
            "demand_score": round(d_norm, 3),
            "supply_score": round(s_norm, 3),
            "ml_listing_count": int(s_raw),
            "matched_ml_query": ml_q,
            "gap_score": round(g_norm, 3),
            "gap_tier": tier,
            "interpretation": _interpret(tier, d_norm, s_norm),
        })

    # Sort by gap_score descending
    opportunities.sort(key=lambda x: x["gap_score"], reverse=True)
    for rank, opp in enumerate(opportunities, start=1):
        opp["rank"] = rank

    return {
        "gap_opportunities": opportunities,
        "metadata": {
            "total_clusters_scored": len(clusters),
            "ml_queries_used": list(ml_supply.keys()),
            "tier_A_count": sum(1 for o in opportunities if o["gap_tier"] == "A"),
            "tier_B_count": sum(1 for o in opportunities if o["gap_tier"] == "B"),
            "tier_C_count": sum(1 for o in opportunities if o["gap_tier"] == "C"),
        },
    }


def _interpret(tier: str, demand: float, supply: float) -> str:
    if tier == "A":
        if supply < 0.1:
            return "Strong demand signal with near-zero supply — high-confidence whitespace."
        return "Strong demand outpacing supply — good sourcing opportunity."
    if tier == "B":
        return "Moderate demand vs supply — worth tracking; validate with deeper search."
    return "Supply appears to meet demand — limited whitespace at current data resolution."
