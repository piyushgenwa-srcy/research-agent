"""TikTok vertical signal collection.

Two-pass strategy:
  Pass 1 — Breadth: multi-keyword + top hashtag crawl → raw post pool ranked by save-to-view ratio.
  Pass 2 — Depth:   comments on top-N posts by save-to-view ratio → sentiment + purchase-intent extraction.

Enhancements:
  - Hashtag co-occurrence clustering for cohort segmentation.
  - Trend velocity: dual-window comparison (30d vs 90d) per keyword.
  - Haiku 4.5 comment classification (falls back to regex if no API key).

Output: a single structured dict written as tiktok_vertical_signal.json.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .comment_classifier import classify_comments
from .connectors.ensemble import EnsembleClient


# ---------------------------------------------------------------------------
# Post normaliser
# ---------------------------------------------------------------------------

def _normalise_post(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten aweme_info wrapper and compute derived metrics."""
    p = raw.get("aweme_info", raw) if isinstance(raw.get("aweme_info"), dict) else raw
    stats = p.get("statistics") or {}
    views = int(stats.get("play_count") or 0)
    likes = int(stats.get("digg_count") or 0)
    saves = int(stats.get("collect_count") or 0)
    comments = int(stats.get("comment_count") or 0)
    shares = int(stats.get("share_count") or 0)

    save_to_view = round(saves / views, 4) if views > 0 else 0.0
    engagement_rate = round((likes + saves + comments + shares) / views, 4) if views > 0 else 0.0

    author = p.get("author") or {}
    # text_extra has type=1 entries with hashtag_name — more reliable than cha_list
    text_extra = p.get("text_extra") or []
    hashtags = [
        h.get("hashtag_name") for h in text_extra
        if h.get("type") == 1 and h.get("hashtag_name")
    ]
    if not hashtags:
        # fallback: cha_list uses cha_name
        hashtags = [h.get("cha_name") for h in (p.get("cha_list") or []) if h.get("cha_name")]

    # Commerce signals
    products_info = p.get("products_info") or p.get("bottom_products") or p.get("right_products")

    aweme_id = str(p.get("aweme_id") or "")
    author_id = str(author.get("unique_id") or author.get("nickname") or "")
    url = (
        p.get("share_url")
        or (p.get("share_info") or {}).get("share_url")
        or (f"https://www.tiktok.com/@{author_id}/video/{aweme_id}" if author_id and aweme_id else "")
    )

    return {
        "aweme_id": aweme_id,
        "desc": str(p.get("desc") or "").strip(),
        "author": author_id,
        "region": p.get("region") or "",
        "create_time": p.get("create_time"),
        "hashtags": hashtags,
        "views": views,
        "likes": likes,
        "saves": saves,
        "comments": comments,
        "shares": shares,
        "save_to_view_ratio": save_to_view,
        "engagement_rate": engagement_rate,
        "is_ads": bool(p.get("is_ads")),
        "products_info": products_info,
        "url": url,
    }


# ---------------------------------------------------------------------------
# Hashtag co-occurrence clustering (BFS connected components)
# ---------------------------------------------------------------------------

def _build_cohort_clusters(
    posts: List[Dict[str, Any]],
    min_co_occurrence: int = 3,
    min_cluster_posts: int = 5,
    generic_hashtags: Optional[set] = None,
) -> List[Dict[str, Any]]:
    """Segment posts into cohort clusters via hashtag co-occurrence.

    Algorithm:
      1. Build hashtag co-occurrence counts from post pool.
      2. Create adjacency list: edge(a,b) when co_occurrence >= min_co_occurrence.
      3. BFS to find connected components (clusters).
      4. Assign each post to the cluster containing the majority of its hashtags.
      5. Summarise each cluster: top hashtags, post count, avg STR.

    Returns:
        List of cluster dicts sorted by avg save-to-view ratio descending.
    """
    if generic_hashtags is None:
        generic_hashtags = {
            "fyp", "foryou", "foryoupage", "viral", "trending", "tiktok",
            "parati", "fypシ", "xyzbca", "moda", "fashion", "ootd",
        }

    # Step 1 — co-occurrence counts
    co_occ: Dict[Tuple[str, str], int] = defaultdict(int)
    hashtag_freq: Dict[str, int] = defaultdict(int)
    for post in posts:
        ht = [h.lower() for h in post.get("hashtags", []) if h and h.lower() not in generic_hashtags]
        for h in ht:
            hashtag_freq[h] += 1
        for i, a in enumerate(ht):
            for b in ht[i + 1:]:
                key = (min(a, b), max(a, b))
                co_occ[key] += 1

    # Step 2 — adjacency list
    adj: Dict[str, set] = defaultdict(set)
    for (a, b), count in co_occ.items():
        if count >= min_co_occurrence:
            adj[a].add(b)
            adj[b].add(a)

    # Step 3 — BFS connected components
    visited: set = set()
    components: List[List[str]] = []
    all_hashtags = set(adj.keys())
    for start in sorted(all_hashtags):
        if start in visited:
            continue
        cluster_nodes: List[str] = []
        queue = [start]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            cluster_nodes.append(node)
            queue.extend(n for n in adj[node] if n not in visited)
        components.append(cluster_nodes)

    # Step 4 — assign posts to clusters
    # For each post, find which component contains the most of its hashtags.
    ht_to_component: Dict[str, int] = {}
    for idx, comp in enumerate(components):
        for ht in comp:
            ht_to_component[ht] = idx

    cluster_posts: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for post in posts:
        ht = [h.lower() for h in post.get("hashtags", []) if h and h.lower() not in generic_hashtags]
        if not ht:
            continue
        # vote: count component assignments
        votes: Dict[int, int] = defaultdict(int)
        for h in ht:
            if h in ht_to_component:
                votes[ht_to_component[h]] += 1
        if not votes:
            continue
        winner = max(votes, key=lambda k: votes[k])
        cluster_posts[winner].append(post)

    # Step 5 — summarise clusters
    clusters: List[Dict[str, Any]] = []
    for comp_idx, comp_nodes in enumerate(components):
        cps = cluster_posts.get(comp_idx, [])
        if len(cps) < min_cluster_posts:
            continue
        avg_str = round(
            sum(p["save_to_view_ratio"] for p in cps) / len(cps), 4
        ) if cps else 0.0
        top_ht = sorted(
            [(h, hashtag_freq[h]) for h in comp_nodes],
            key=lambda x: x[1],
            reverse=True,
        )[:10]
        clusters.append({
            "cluster_id": comp_idx,
            "top_hashtags": [h for h, _ in top_ht],
            "hashtag_freq_in_pool": {h: f for h, f in top_ht},
            "post_count": len(cps),
            "avg_save_to_view_ratio": avg_str,
            "total_views": sum(p["views"] for p in cps),
            "total_saves": sum(p["saves"] for p in cps),
        })

    return sorted(clusters, key=lambda c: c["avg_save_to_view_ratio"], reverse=True)


# ---------------------------------------------------------------------------
# Pass 1 — Breadth
# ---------------------------------------------------------------------------

def _collect_hashtag_posts(client: EnsembleClient, hashtag: str) -> List[Dict[str, Any]]:
    try:
        resp = client.tiktok_hashtag_posts(hashtag)
        data = resp.get("data", {})
        raw = data.get("data", []) if isinstance(data, dict) else []
        return [_normalise_post(p) for p in raw if isinstance(p, dict)]
    except Exception:
        return []


def collect_breadth(
    client: EnsembleClient,
    keywords: List[str],
    period: int = 90,
    max_pages_per_keyword: int = 3,
    max_hashtag_expansion: int = 5,
) -> Dict[str, Any]:
    """Collect a wide post pool across keywords + top hashtags."""
    posts_by_keyword: Dict[str, List[Dict[str, Any]]] = {}
    seen_ids: set = set()
    all_posts: List[Dict[str, Any]] = []

    for kw in keywords:
        raw = client.tiktok_keyword_search_all(kw, period=period, max_pages=max_pages_per_keyword)
        normalised = [_normalise_post(p) for p in raw]
        posts_by_keyword[kw] = normalised
        for p in normalised:
            if p["aweme_id"] and p["aweme_id"] not in seen_ids:
                seen_ids.add(p["aweme_id"])
                all_posts.append(p)

    # Hashtag frequency across all posts
    hashtag_freq: Dict[str, int] = {}
    for p in all_posts:
        for h in p["hashtags"]:
            if h:
                hashtag_freq[h.lower()] = hashtag_freq.get(h.lower(), 0) + 1

    # Expand with top hashtags (exclude generic ones already covered by keywords)
    generic = {"fyp", "foryou", "foryoupage", "viral", "trending", "tiktok", "parati", "fypシ", "xyzbca"}
    top_hashtags = sorted(
        [h for h in hashtag_freq if h not in generic],
        key=lambda h: hashtag_freq[h],
        reverse=True,
    )[:max_hashtag_expansion]

    hashtag_posts: Dict[str, List[Dict[str, Any]]] = {}
    for ht in top_hashtags:
        expanded = _collect_hashtag_posts(client, ht)
        hashtag_posts[ht] = expanded
        for p in expanded:
            if p["aweme_id"] and p["aweme_id"] not in seen_ids:
                seen_ids.add(p["aweme_id"])
                all_posts.append(p)

    # Sort by save-to-view ratio (purchase intent) then by raw saves as tiebreak
    all_posts.sort(key=lambda p: (p["save_to_view_ratio"], p["saves"]), reverse=True)

    return {
        "keywords_searched": keywords,
        "hashtags_expanded": top_hashtags,
        "hashtag_frequency": dict(sorted(hashtag_freq.items(), key=lambda x: x[1], reverse=True)[:50]),
        "total_posts_collected": len(all_posts),
        "posts_by_keyword": {kw: len(v) for kw, v in posts_by_keyword.items()},
        "posts_by_hashtag": {ht: len(v) for ht, v in hashtag_posts.items()},
        "post_pool": all_posts,
    }


# ---------------------------------------------------------------------------
# Trend velocity: 30d vs 90d window comparison
# ---------------------------------------------------------------------------

def collect_trend_velocity(
    client: EnsembleClient,
    keywords: List[str],
    max_pages_per_keyword: int = 2,
) -> Dict[str, Any]:
    """Compare save-to-view ratio at 30d vs 90d window per keyword.

    Returns per-keyword velocity metrics and an overall acceleration score.
    """
    velocity_by_keyword: Dict[str, Dict[str, Any]] = {}

    for kw in keywords:
        window_data: Dict[int, Dict[str, Any]] = {}
        for days in (30, 90):
            posts_raw = client.tiktok_keyword_search_all(kw, period=days, max_pages=max_pages_per_keyword)
            posts = [_normalise_post(p) for p in posts_raw]
            total_views = sum(p["views"] for p in posts)
            total_saves = sum(p["saves"] for p in posts)
            avg_str = round(
                sum(p["save_to_view_ratio"] for p in posts) / len(posts), 4
            ) if posts else 0.0
            window_data[days] = {
                "post_count": len(posts),
                "total_views": total_views,
                "total_saves": total_saves,
                "avg_save_to_view_ratio": avg_str,
            }

        str_30 = window_data[30]["avg_save_to_view_ratio"]
        str_90 = window_data[90]["avg_save_to_view_ratio"]
        if str_90 > 0:
            velocity = round((str_30 - str_90) / str_90, 4)
        else:
            velocity = 0.0

        if velocity > 0.25:
            trend_label = "accelerating"
        elif velocity > 0.05:
            trend_label = "growing"
        elif velocity < -0.25:
            trend_label = "declining"
        elif velocity < -0.05:
            trend_label = "slowing"
        else:
            trend_label = "stable"

        velocity_by_keyword[kw] = {
            "window_30d": window_data[30],
            "window_90d": window_data[90],
            "str_velocity": velocity,
            "trend_label": trend_label,
        }

    # Overall: average velocity across keywords
    velocities = [v["str_velocity"] for v in velocity_by_keyword.values()]
    avg_velocity = round(sum(velocities) / len(velocities), 4) if velocities else 0.0

    return {
        "keywords": velocity_by_keyword,
        "avg_velocity": avg_velocity,
        "top_accelerating": [
            kw for kw, v in sorted(
                velocity_by_keyword.items(),
                key=lambda x: x[1]["str_velocity"],
                reverse=True,
            )
            if v["str_velocity"] > 0.05
        ][:5],
    }


# ---------------------------------------------------------------------------
# Pass 2 — Depth (comments)
# ---------------------------------------------------------------------------

def _extract_comments(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = resp.get("data", {})
    raw = data.get("comments", []) if isinstance(data, dict) else []
    out = []
    for c in raw:
        if not isinstance(c, dict):
            continue
        text = str(c.get("text") or "").strip()
        if not text:
            continue
        out.append({
            "cid": str(c.get("cid") or ""),
            "text": text,
            "likes": int(c.get("digg_count") or 0),
            "reply_count": int(c.get("reply_comment_total") or 0),
            "is_high_purchase_intent": bool(c.get("is_high_purchase_intent")),
        })
    return out


def collect_depth(
    client: EnsembleClient,
    post_pool: List[Dict[str, Any]],
    top_n: int = 20,
    anthropic_api_key: Optional[str] = None,
    product_context: str = "",
) -> List[Dict[str, Any]]:
    """Fetch comments for top-N posts (ranked by save-to-view ratio).

    Skips ads. Deduplicates by aweme_id. Returns list of post dicts
    augmented with comment data and per-theme comment counts.

    If anthropic_api_key is provided, Haiku 4.5 is used for comment
    classification. Otherwise falls back to regex.
    """
    candidates = [p for p in post_pool if not p.get("is_ads") and p.get("aweme_id")]
    top = candidates[:top_n]
    results = []
    for post in top:
        aweme_id = post["aweme_id"]
        try:
            resp = client.tiktok_post_comments(aweme_id)
            raw_comments = _extract_comments(resp)
        except Exception:
            raw_comments = []

        # Classify comments (Haiku or regex)
        texts = [c["text"] for c in raw_comments]
        classifications = classify_comments(texts, anthropic_api_key, product_context) if texts else []

        theme_counts: Dict[str, int] = {}
        high_intent_comments = []
        classified_comments = []
        for raw_c, cls in zip(raw_comments, classifications):
            enriched = {
                **raw_c,
                "themes": cls.get("themes", ["other"]),
                "sentiment": cls.get("sentiment", "neutral"),
                "purchase_intent_score": cls.get("purchase_intent_score", 0.0),
                "key_phrase": cls.get("key_phrase"),
                "classifier": cls.get("classifier", "regex"),
            }
            classified_comments.append(enriched)
            for t in enriched["themes"]:
                theme_counts[t] = theme_counts.get(t, 0) + 1
            if raw_c.get("is_high_purchase_intent") or enriched["purchase_intent_score"] >= 0.7:
                high_intent_comments.append(raw_c["text"])

        results.append({
            **post,
            "fetched_comments": classified_comments,
            "comment_theme_counts": theme_counts,
            "high_intent_comment_count": len(high_intent_comments),
            "high_intent_samples": high_intent_comments[:5],
            "top_liked_comments": sorted(
                classified_comments, key=lambda c: c["likes"], reverse=True
            )[:5],
            "comment_sentiment_summary": {
                "positive": sum(1 for c in classified_comments if c["sentiment"] == "positive"),
                "negative": sum(1 for c in classified_comments if c["sentiment"] == "negative"),
                "neutral": sum(1 for c in classified_comments if c["sentiment"] == "neutral"),
            },
        })

    return results


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def collect_vertical_signal(
    client: EnsembleClient,
    keywords: List[str],
    period: int = 90,
    max_pages_per_keyword: int = 3,
    max_hashtag_expansion: int = 5,
    depth_top_n: int = 20,
    anthropic_api_key: Optional[str] = None,
    product_context: str = "",
    include_trend_velocity: bool = True,
) -> Dict[str, Any]:
    """Full two-pass vertical collection. Returns a dict ready for JSON serialisation.

    Args:
        client:               EnsembleClient instance.
        keywords:             6-12 keyword variants covering the category.
        period:               Primary lookback window in days (default 90).
        max_pages_per_keyword: Pages to paginate per keyword (default 3).
        max_hashtag_expansion: How many hashtags to expand in breadth pass.
        depth_top_n:          Top-N posts to fetch comments for.
        anthropic_api_key:    If provided, Haiku 4.5 is used for comment classification.
        product_context:      Optional product/category description for the classifier.
        include_trend_velocity: Whether to run the 30d vs 90d velocity comparison.
    """
    breadth = collect_breadth(
        client,
        keywords=keywords,
        period=period,
        max_pages_per_keyword=max_pages_per_keyword,
        max_hashtag_expansion=max_hashtag_expansion,
    )
    deep_posts = collect_depth(
        client,
        breadth["post_pool"],
        top_n=depth_top_n,
        anthropic_api_key=anthropic_api_key,
        product_context=product_context,
    )

    # Cohort clustering
    cohort_clusters = _build_cohort_clusters(breadth["post_pool"])

    # Trend velocity (separate API calls, lighter page count)
    trend_velocity: Dict[str, Any] = {}
    if include_trend_velocity:
        try:
            trend_velocity = collect_trend_velocity(
                client, keywords, max_pages_per_keyword=min(max_pages_per_keyword, 2)
            )
        except Exception:
            trend_velocity = {"error": "velocity collection failed"}

    # Summary stats
    pool = breadth["post_pool"]
    top_by_views = sorted(pool, key=lambda p: p["views"], reverse=True)[:10]
    top_by_saves = sorted(pool, key=lambda p: p["saves"], reverse=True)[:10]
    top_by_str = sorted(pool, key=lambda p: p["save_to_view_ratio"], reverse=True)[:10]

    # Aggregate complaint and opportunity signals from depth
    all_complaints: List[str] = []
    all_want_to_buy: List[str] = []
    all_high_intent_key_phrases: List[str] = []
    for dp in deep_posts:
        for c in dp.get("fetched_comments", []):
            if "complaint" in c.get("themes", []):
                all_complaints.append(c["text"])
            if "want_to_buy" in c.get("themes", []):
                all_want_to_buy.append(c["text"])
            if c.get("key_phrase") and c.get("purchase_intent_score", 0) >= 0.6:
                all_high_intent_key_phrases.append(c["key_phrase"])

    # Deduplicate key phrases
    seen_phrases: set = set()
    unique_phrases: List[str] = []
    for phrase in all_high_intent_key_phrases:
        if phrase.lower() not in seen_phrases:
            seen_phrases.add(phrase.lower())
            unique_phrases.append(phrase)

    return {
        "period_days": period,
        "keywords_searched": breadth["keywords_searched"],
        "hashtags_expanded": breadth["hashtags_expanded"],
        "hashtag_frequency": breadth["hashtag_frequency"],
        "total_posts_collected": breadth["total_posts_collected"],
        "posts_by_keyword": breadth["posts_by_keyword"],
        "posts_by_hashtag": breadth["posts_by_hashtag"],
        "post_pool": pool,
        "top_by_views": top_by_views,
        "top_by_saves": top_by_saves,
        "top_by_save_to_view_ratio": top_by_str,
        "cohort_clusters": cohort_clusters,
        "trend_velocity": trend_velocity,
        "deep_posts": deep_posts,
        "demand_signals": {
            "complaint_samples": all_complaints[:20],
            "want_to_buy_samples": all_want_to_buy[:20],
            "total_complaints_found": len(all_complaints),
            "total_want_to_buy_found": len(all_want_to_buy),
            "high_intent_key_phrases": unique_phrases[:30],
        },
    }
