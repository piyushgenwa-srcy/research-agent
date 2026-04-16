from __future__ import annotations

from html import unescape
import re
from typing import Any, Dict, List, Optional

from .models import (
    EvidenceCandidate,
    EvidenceItem,
    EvidenceMetrics,
    ExcludedItem,
    LaneEvidencePack,
    LanePlan,
    ClientProfile,
)


# --- MercadoLibre item ID patterns -----------------------------------------
# Each MercadoLibre country site uses a distinct prefix: MLM (MX), MLA (AR),
# MLB (BR), MCO (CO), MLC (CL), etc.
_ML_ITEM_ID_RE = re.compile(r'\b(ML[A-Z])-?(\d{7,12})\b', re.IGNORECASE)

# MercadoLibre money amount: integer fraction of price, e.g. "1,299"
_ML_PRICE_RE = re.compile(
    r'class="[^"]*andes-money-amount__fraction[^"]*"[^>]*>\s*'
    r'([\d,\.]+)\s*<',
    re.IGNORECASE,
)

# MercadoLibre review rating, e.g. "4.5" or "(123)"
_ML_RATING_RE = re.compile(
    r'class="[^"]*(?:reviews__rating|rating-number)[^"]*"[^>]*>\s*'
    r'([\d.]+)\s*<',
    re.IGNORECASE,
)
_ML_REVIEW_COUNT_RE = re.compile(
    r'class="[^"]*(?:reviews__total|reviews__amount|reviews-amount)[^"]*"[^>]*>\s*'
    r'\(?([\d,\.]+)\)?\s*<',
    re.IGNORECASE,
)


def _flatten_dict_candidates(node: Any, out: List[Dict[str, Any]]) -> None:
    if isinstance(node, dict):
        out.append(node)
        for value in node.values():
            _flatten_dict_candidates(value, out)
    elif isinstance(node, list):
        for item in node:
            _flatten_dict_candidates(item, out)


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    match = re.search(r"\d+(?:\.\d+)?", text.replace(",", ""))
    return float(match.group(0)) if match else None


def _as_int(value: Any) -> Optional[int]:
    num = _as_float(value)
    return int(num) if num is not None else None


def _extract_html_text(response: Dict[str, Any]) -> Optional[str]:
    dicts: List[Dict[str, Any]] = []
    _flatten_dict_candidates(response, dicts)
    for item in dicts:
        for key in ("content", "html", "page_content", "source"):
            value = item.get(key)
            if isinstance(value, str) and "<html" in value.lower():
                return value
    return None


def _extract_structured_products(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    dicts: List[Dict[str, Any]] = []
    _flatten_dict_candidates(response, dicts)
    products: List[Dict[str, Any]] = []
    for item in dicts:
        title = item.get("title") or item.get("name") or item.get("product_title")
        url = item.get("url") or item.get("product_url")
        if not isinstance(title, str) or not title.strip():
            continue
        if not isinstance(url, str) or "amazon." not in url:
            continue
        products.append(item)
    return products


def _extract_html_products(html: str) -> List[Dict[str, Any]]:
    products: List[Dict[str, Any]] = []
    seen: set[str] = set()
    pattern = re.compile(
        r'data-asin="(?P<asin>[A-Z0-9]{10})".*?'
        r'href="(?P<href>/[^"]*/dp/(?P=asin)[^"]*)".*?'
        r'<span[^>]*>(?P<title>[^<]{8,200})</span>',
        re.DOTALL,
    )
    for match in pattern.finditer(html):
        asin = match.group("asin")
        if asin in seen:
            continue
        seen.add(asin)
        title = " ".join(unescape(match.group("title")).split())
        href = unescape(match.group("href"))
        products.append(
            {
                "asin": asin,
                "title": title,
                "url": f"https://www.amazon.com{href}",
            }
        )
    return products


def _normalize_title(title: str) -> str:
    normalized = re.sub(r"\b[A-Z0-9]{10}\b", "", title)
    normalized = re.sub(r"\s+", " ", normalized).strip(" -,:")
    return normalized or title


def build_amazon_evidence_pack(
    response: Dict[str, Any],
    query: str,
    lane_plan: LanePlan,
    client_profile: ClientProfile,
    raw_response_path: str,
) -> LaneEvidencePack:
    warnings: List[str] = []
    excluded: List[ExcludedItem] = []
    candidates: List[EvidenceCandidate] = []

    structured = _extract_structured_products(response)
    html = _extract_html_text(response)
    html_products = _extract_html_products(html) if html else []
    products = structured if structured else html_products

    if not products:
        warnings.append("No product candidates could be parsed from the Oxylabs response.")
    if structured and html_products:
        warnings.append("Both structured and HTML product hints were available; using structured candidates first.")
    if not structured and html_products:
        warnings.append("Fell back to HTML parsing because no structured Amazon product objects were found.")
    if html is None:
        warnings.append("No HTML payload found in the raw response.")

    for index, product in enumerate(products[:10], start=1):
        title = str(product.get("title") or product.get("name") or product.get("product_title") or "").strip()
        url = str(product.get("url") or product.get("product_url") or "")
        if not title or not url:
            continue
        normalized = _normalize_title(title)
        price = _as_float(product.get("price"))
        rating = _as_float(product.get("rating"))
        review_count = _as_int(product.get("review_count") or product.get("reviews_count"))
        evidence_item = EvidenceItem(
            source_id=str(product.get("asin") or url),
            source_type="listing",
            title_or_caption=title,
            creator_or_seller=product.get("brand") or product.get("seller_name"),
            published_at=None,
            metrics=EvidenceMetrics(
                rank=index,
                review_count=review_count,
                rating=rating,
                price=price,
            ),
            is_original_signal=True,
            repost_suspected=False,
            evidence_note=f"Parsed from Amazon search results for query '{query}'.",
        )
        flags: List[str] = []
        if price is None:
            flags.append("missing price")
        if review_count is None:
            flags.append("missing review_count")
        if rating is None:
            flags.append("missing rating")
        candidates.append(
            EvidenceCandidate(
                source_product_label=title,
                normalized_product_name=normalized,
                generic_format_note="Amazon-derived generic format candidate; needs tighter normalization before sourcing.",
                evidence_items=[evidence_item],
                evidence_count=1,
                naming_uncertainty=[],
                data_quality_flags=flags,
                collection_note="First-pass Amazon listing candidate from connector-backed search.",
            )
        )

    if len(products) > len(candidates):
        excluded.append(
            ExcludedItem(
                source_product_label="unparsed Amazon listings",
                reason="some result objects lacked a parseable title or URL",
            )
        )

    lane_target = next((lane for lane in lane_plan.lanes if lane.lane == "amazon"), None)
    search_objective = lane_target.search_objective if lane_target else f"Amazon search for {query}"
    return LaneEvidencePack(
        lane="amazon",
        search_objective=search_objective,
        client_scope={
            "platform": client_profile.platform,
            "markets": client_profile.markets,
            "categories": client_profile.categories,
            "trend_definition": client_profile.trend_definition,
            "query": query,
        },
        candidates=candidates,
        extraction_warnings=warnings,
        excluded_items=excluded,
        raw_response_path=raw_response_path,
    )


def _extract_tiktok_posts(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    data = response.get("data")
    if isinstance(data, dict):
        posts = data.get("data") or data.get("posts")
        if isinstance(posts, list):
            return [item for item in posts if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _nested_get_str(item: Dict[str, Any], keys: List[str]) -> Optional[str]:
    current: Any = item
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, str) else None


def build_tiktok_evidence_pack(
    response: Dict[str, Any],
    keyword: str,
    lane_plan: LanePlan,
    client_profile: ClientProfile,
    raw_response_path: str,
) -> LaneEvidencePack:
    warnings: List[str] = []
    candidates: List[EvidenceCandidate] = []
    excluded: List[ExcludedItem] = []
    posts = _extract_tiktok_posts(response)
    if not posts:
        warnings.append("No TikTok posts could be parsed from the Ensemble response.")

    for post in posts[:10]:
        aweme = post.get("aweme_info") if isinstance(post.get("aweme_info"), dict) else post
        title = (
            _nested_get_str(aweme, ["desc"])
            or _nested_get_str(aweme, ["text"])
            or _nested_get_str(aweme, ["caption"])
            or _nested_get_str(aweme, ["descText"])
            or ""
        ).strip()
        if not title:
            title = "TikTok post without parsed caption"
        post_id = _nested_get_str(aweme, ["aweme_id"]) or _nested_get_str(aweme, ["id"]) or title
        author = (
            _nested_get_str(aweme, ["author", "unique_id"])
            or _nested_get_str(aweme, ["author", "nickname"])
            or _nested_get_str(aweme, ["author", "username"])
        )
        post_url = (
            _nested_get_str(aweme, ["share_url"])
            or _nested_get_str(aweme, ["share_info", "share_url"])
            or _nested_get_str(aweme, ["url"])
            or _nested_get_str(aweme, ["video_url"])
            or f"https://www.tiktok.com/@{author}/video/{post_id}" if author and post_id else str(post_id)
        )
        stats = aweme.get("statistics") if isinstance(aweme.get("statistics"), dict) else {}
        views = _as_int(stats.get("play_count") if isinstance(stats, dict) else None)
        likes = _as_int(stats.get("digg_count") if isinstance(stats, dict) else None)
        comments = _as_int(stats.get("comment_count") if isinstance(stats, dict) else None)
        candidate_name = title[:120]
        flags: List[str] = []
        if views is None:
            flags.append("missing views")
        if likes is None:
            flags.append("missing likes")
        if comments is None:
            flags.append("missing comments")
        candidates.append(
            EvidenceCandidate(
                source_product_label=title,
                normalized_product_name=candidate_name,
                generic_format_note="TikTok-derived candidate; needs keyword clustering and format normalization before synthesis.",
                evidence_items=[
                    EvidenceItem(
                        source_id=str(post_id),
                        source_type="post",
                        title_or_caption=title,
                        creator_or_seller=author,
                        published_at=str(aweme.get("create_time")) if aweme.get("create_time") is not None else None,
                        metrics=EvidenceMetrics(
                            views=views,
                            likes=likes,
                            comments=comments,
                        ),
                        is_original_signal=True,
                        repost_suspected=False,
                        evidence_note=f"Parsed from Ensemble TikTok keyword search for '{keyword}'.",
                    )
                ],
                evidence_count=1,
                naming_uncertainty=[],
                data_quality_flags=flags,
                collection_note=f"First-pass TikTok post candidate for keyword '{keyword}'.",
            )
        )
        if not post_url:
            excluded.append(
                ExcludedItem(
                    source_product_label=title,
                    reason="missing parseable post URL",
                )
            )

    lane_target = next((lane for lane in lane_plan.lanes if lane.lane == "tiktok"), None)
    search_objective = lane_target.search_objective if lane_target else f"TikTok search for {keyword}"
    return LaneEvidencePack(
        lane="tiktok",
        search_objective=search_objective,
        client_scope={
            "platform": client_profile.platform,
            "markets": client_profile.markets,
            "categories": client_profile.categories,
            "trend_definition": client_profile.trend_definition,
            "query": keyword,
        },
        candidates=candidates,
        extraction_warnings=warnings,
        excluded_items=excluded,
        raw_response_path=raw_response_path,
    )


# ---------------------------------------------------------------------------
# MercadoLibre extractor
# ---------------------------------------------------------------------------

def _extract_ml_item_id(url: str) -> Optional[str]:
    """Return a normalised ML item ID (e.g. 'MLM1234567890') from a product URL."""
    match = _ML_ITEM_ID_RE.search(url)
    if not match:
        return None
    return match.group(1).upper() + match.group(2)


def _extract_ml_structured_products(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Try to pull structured product dicts from an Oxylabs response.

    Oxylabs' universal scraper does not parse MercadoLibre into a structured
    product list, but this handles any future cases where Oxylabs returns
    parsed e-commerce objects.
    """
    dicts: List[Dict[str, Any]] = []
    _flatten_dict_candidates(response, dicts)
    products = []
    for item in dicts:
        title = item.get("title") or item.get("name") or item.get("product_title")
        url = item.get("url") or item.get("product_url") or item.get("link")
        if not isinstance(title, str) or not title.strip():
            continue
        if not isinstance(url, str) or "mercadolibre." not in url:
            continue
        if not _extract_ml_item_id(url):
            continue
        products.append(item)
    return products


def _extract_ml_html_products(html: str) -> List[Dict[str, Any]]:
    """Parse MercadoLibre search result HTML for product candidates.

    ML's search-nordic page (Next.js SSR) renders each product inside a
    ``ui-search-result__wrapper`` div using polycard components.  The
    traditional approach of matching ``<a href="mercadolibre…">title</a>``
    fails because product links go through a click-tracking redirect.

    Strategy:
    1. Split the HTML on ``ui-search-result__wrapper`` to isolate per-product
       blocks (avoids fragile full-page regex).
    2. Per block: extract title from the ``poly-component__title`` anchor text,
       item ID from the ``wid=MLM…`` query parameter in the click URL, and
       price from the ``andes-money-amount__fraction`` span.
    3. Rating and review count are not present in the grid HTML; set to None.
    """
    products: List[Dict[str, Any]] = []
    seen: set[str] = set()

    # Split on each product wrapper boundary
    wrapper_re = re.compile(
        r'ui-search-result__wrapper">(.*?)(?=ui-search-result__wrapper"|<footer|</ol\b)',
        re.DOTALL,
    )
    title_re = re.compile(r'class="poly-component__title"[^>]*>([^<]{5,250})<', re.IGNORECASE)
    wid_re = re.compile(r'wid=(ML[A-Z]\d{7,12})', re.IGNORECASE)
    price_re = re.compile(r'andes-money-amount__fraction[^>]*>([\d,\.]+)<', re.IGNORECASE)

    for wrapper_match in wrapper_re.finditer(html):
        block = wrapper_match.group(1)
        title_m = title_re.search(block)
        if not title_m:
            continue
        title = " ".join(unescape(title_m.group(1)).split()).strip()
        if len(title) < 8:
            continue
        wid_m = wid_re.search(block)
        item_id = wid_m.group(1) if wid_m else None
        if item_id and item_id in seen:
            continue
        if item_id:
            seen.add(item_id)
        price_m = price_re.search(block)
        price_str = price_m.group(1).replace(",", "").replace(".", "") if price_m else None
        # ML fractions are integer pesos (no decimal separator)
        price = float(price_str) if price_str else None
        products.append({
            "item_id": item_id,
            "title": title,
            "url": f"https://www.mercadolibre.com.mx/{item_id}" if item_id else "",
            "price": price,
        })

    return products


def _extract_ml_page_scalars(html: str) -> Dict[str, Optional[float]]:
    """Extract page-level aggregate scalars (first match only) from ML HTML.

    These are best-effort: MercadoLibre's HTML class names change across A/B
    tests. Callers should treat None as missing, not as zero.
    """
    price_match = _ML_PRICE_RE.search(html)
    rating_match = _ML_RATING_RE.search(html)
    review_match = _ML_REVIEW_COUNT_RE.search(html)
    return {
        "price": _as_float(price_match.group(1).replace(",", "") if price_match else None),
        "rating": _as_float(rating_match.group(1) if rating_match else None),
        "review_count": _as_float(review_match.group(1).replace(",", "") if review_match else None),
    }


def build_mercadolibre_evidence_pack(
    response: Dict[str, Any],
    query: str,
    lane_plan: LanePlan,
    client_profile: ClientProfile,
    raw_response_path: str,
    domain: str = "com.mx",
) -> LaneEvidencePack:
    """Build a lane_evidence_pack from an Oxylabs MercadoLibre scrape response.

    Tries structured extraction first, falls back to HTML parsing. Page-level
    scalars (price, rating, review_count) are extracted from the HTML when
    available but are frequently missing and flagged accordingly.
    """
    warnings: List[str] = []
    excluded: List[ExcludedItem] = []
    candidates: List[EvidenceCandidate] = []

    structured = _extract_ml_structured_products(response)
    html = _extract_html_text(response)
    html_products = _extract_ml_html_products(html) if html else []
    products = structured if structured else html_products

    if not products:
        warnings.append("No product candidates could be parsed from the Oxylabs MercadoLibre response.")
    if structured and html_products:
        warnings.append("Both structured and HTML product hints available; using structured candidates.")
    if not structured and html_products:
        warnings.append("Fell back to HTML parsing — no structured ML product objects found.")
    if html is None:
        warnings.append("No HTML payload found in the raw response.")

    # Extract page-level scalars once for use as a fallback when per-item data
    # is unavailable (HTML parsing rarely yields per-item price/rating).
    page_scalars = _extract_ml_page_scalars(html) if html else {}

    for index, product in enumerate(products[:10], start=1):
        title = str(product.get("title") or product.get("name") or "").strip()
        url = str(product.get("url") or product.get("product_url") or product.get("link") or "")
        item_id = _extract_ml_item_id(url) or product.get("item_id") or url
        if not title or not url:
            continue

        # Per-item scalars from structured data; fall back to page-level scalars.
        price = _as_float(product.get("price")) or page_scalars.get("price")
        rating = _as_float(product.get("rating")) or page_scalars.get("rating")
        review_count = _as_int(product.get("review_count") or product.get("reviews_count")) or (
            int(page_scalars["review_count"]) if page_scalars.get("review_count") else None
        )
        seller = product.get("seller_name") or product.get("brand") or product.get("seller")

        flags: List[str] = []
        if price is None:
            flags.append("missing price")
        if rating is None:
            flags.append("missing rating")
        if review_count is None:
            flags.append("missing review_count")
        if page_scalars and (price or rating or review_count):
            flags.append("scalars are page-level proxies, not per-item")

        evidence_item = EvidenceItem(
            source_id=str(item_id),
            source_type="listing",
            title_or_caption=title,
            creator_or_seller=seller,
            published_at=None,
            metrics=EvidenceMetrics(
                rank=index,
                price=price,
                rating=rating,
                review_count=review_count,
            ),
            is_original_signal=True,
            repost_suspected=False,
            evidence_note=f"Parsed from MercadoLibre search results for query '{query}' on {domain}.",
        )
        candidates.append(
            EvidenceCandidate(
                source_product_label=title,
                normalized_product_name=title,
                generic_format_note=(
                    "MercadoLibre-derived listing candidate; requires format normalisation "
                    "and sentiment extraction from reviews before private label spec work."
                ),
                evidence_items=[evidence_item],
                evidence_count=1,
                naming_uncertainty=[],
                data_quality_flags=flags,
                collection_note=f"First-pass MercadoLibre listing candidate from HTML scrape on {domain}.",
            )
        )

    if len(products) > len(candidates):
        excluded.append(
            ExcludedItem(
                source_product_label="unparsed MercadoLibre listings",
                reason="result objects lacked a parseable title, URL, or ML item ID",
            )
        )

    lane_target = next((lane for lane in lane_plan.lanes if lane.lane == "mercadolibre"), None)
    search_objective = lane_target.search_objective if lane_target else f"MercadoLibre search for {query} on {domain}"
    return LaneEvidencePack(
        lane="mercadolibre",
        search_objective=search_objective,
        client_scope={
            "platform": client_profile.platform,
            "markets": client_profile.markets,
            "categories": client_profile.categories,
            "trend_definition": client_profile.trend_definition,
            "query": query,
            "domain": domain,
        },
        candidates=candidates,
        extraction_warnings=warnings,
        excluded_items=excluded,
        raw_response_path=raw_response_path,
    )


# ---------------------------------------------------------------------------
# Instagram extractor (SerpAPI Google site:instagram.com)
# ---------------------------------------------------------------------------

def build_instagram_evidence_pack(
    response: Dict[str, Any],
    keyword: str,
    lane_plan: LanePlan,
    client_profile: ClientProfile,
    raw_response_path: str,
) -> LaneEvidencePack:
    """Build a lane_evidence_pack from a SerpAPI Google site:instagram.com response.

    Each organic result maps to one candidate.  The post caption comes from the
    Google snippet; engagement metrics are unavailable via this method and are
    set to None.
    """
    warnings: List[str] = []
    candidates: List[EvidenceCandidate] = []
    excluded: List[ExcludedItem] = []

    organic = response.get("organic_results") or []
    if not organic:
        warnings.append("No organic_results in SerpAPI response.")

    for index, result in enumerate(organic[:15], start=1):
        title = str(result.get("title") or "").strip()
        snippet = str(result.get("snippet") or "").strip()
        link = str(result.get("link") or "").strip()
        if not link or "instagram.com" not in link:
            excluded.append(ExcludedItem(source_product_label=title or link, reason="result not an Instagram URL"))
            continue
        caption = snippet or title
        if not caption:
            excluded.append(ExcludedItem(source_product_label=link, reason="no caption or snippet available"))
            continue
        post_id_m = re.search(r"/(?:p|reel)/([A-Za-z0-9_-]+)", link)
        post_id = post_id_m.group(1) if post_id_m else link

        candidates.append(
            EvidenceCandidate(
                source_product_label=caption[:120],
                normalized_product_name=caption[:120],
                generic_format_note=(
                    "Instagram-derived candidate via Google search; caption is the trend signal. "
                    "No engagement metrics available — rank from Google SERP position used as proxy."
                ),
                evidence_items=[
                    EvidenceItem(
                        source_id=post_id,
                        source_type="post",
                        title_or_caption=caption,
                        creator_or_seller=None,
                        published_at=None,
                        metrics=EvidenceMetrics(
                            rank=index,
                            views=None,
                            likes=None,
                            comments=None,
                        ),
                        is_original_signal=True,
                        repost_suspected=False,
                        evidence_note=(
                            f"Sourced from Google site:instagram.com search for '{keyword}'. "
                            f"URL: {link}"
                        ),
                    )
                ],
                evidence_count=1,
                naming_uncertainty=[],
                data_quality_flags=["no engagement metrics — SERP rank proxy only"],
                collection_note=f"Instagram Google-search candidate for keyword '{keyword}'.",
            )
        )

    lane_target = next((lane for lane in lane_plan.lanes if lane.lane == "instagram"), None)
    search_objective = lane_target.search_objective if lane_target else f"Instagram search for {keyword}"
    return LaneEvidencePack(
        lane="instagram",
        search_objective=search_objective,
        client_scope={
            "platform": client_profile.platform,
            "markets": client_profile.markets,
            "categories": client_profile.categories,
            "trend_definition": client_profile.trend_definition,
            "query": keyword,
        },
        candidates=candidates,
        extraction_warnings=warnings,
        excluded_items=excluded,
        raw_response_path=raw_response_path,
    )


# ---------------------------------------------------------------------------
# Pinterest extractor (SerpAPI Google site:pinterest.com)
# ---------------------------------------------------------------------------

def build_pinterest_evidence_pack(
    response: Dict[str, Any],
    keyword: str,
    lane_plan: LanePlan,
    client_profile: ClientProfile,
    raw_response_path: str,
) -> LaneEvidencePack:
    """Build a lane_evidence_pack from a SerpAPI Google site:pinterest.com response.

    Pinterest results are visual-dominant and skew toward the 28-45 cohort.
    Each organic result maps to one candidate.  The pin title/snippet is
    the trend signal; engagement metrics are unavailable.
    """
    warnings: List[str] = []
    candidates: List[EvidenceCandidate] = []
    excluded: List[ExcludedItem] = []

    organic = response.get("organic_results") or []
    if not organic:
        warnings.append("No organic_results in SerpAPI response.")

    for index, result in enumerate(organic[:15], start=1):
        title = str(result.get("title") or "").strip()
        snippet = str(result.get("snippet") or "").strip()
        link = str(result.get("link") or "").strip()
        if not link or "pinterest.com" not in link:
            excluded.append(ExcludedItem(
                source_product_label=title or link,
                reason="result not a Pinterest URL",
            ))
            continue
        caption = snippet or title
        if not caption:
            excluded.append(ExcludedItem(source_product_label=link, reason="no caption or snippet available"))
            continue

        # Extract pin ID from URL if available (e.g. /pin/12345/)
        pin_id_m = re.search(r"/pin/(\d+)", link)
        pin_id = pin_id_m.group(1) if pin_id_m else link

        candidates.append(
            EvidenceCandidate(
                source_product_label=caption[:120],
                normalized_product_name=caption[:120],
                generic_format_note=(
                    "Pinterest-derived candidate via Google site:pinterest.com search. "
                    "Strong signal for 28-45 cohort and aspirational style trends. "
                    "No engagement metrics available — SERP rank used as proxy."
                ),
                evidence_items=[
                    EvidenceItem(
                        source_id=pin_id,
                        source_type="pin",
                        title_or_caption=caption,
                        creator_or_seller=None,
                        published_at=None,
                        metrics=EvidenceMetrics(
                            rank=index,
                            views=None,
                            likes=None,
                            comments=None,
                        ),
                        is_original_signal=True,
                        repost_suspected=False,
                        evidence_note=(
                            f"Sourced from Google site:pinterest.com search for '{keyword}'. "
                            f"URL: {link}"
                        ),
                    )
                ],
                evidence_count=1,
                naming_uncertainty=[],
                data_quality_flags=["no engagement metrics — SERP rank proxy only", "pinterest cohort: 28-45"],
                collection_note=f"Pinterest Google-search candidate for keyword '{keyword}'.",
            )
        )

    lane_target = next((lane for lane in lane_plan.lanes if lane.lane == "pinterest"), None)
    search_objective = lane_target.search_objective if lane_target else f"Pinterest search for {keyword}"
    return LaneEvidencePack(
        lane="pinterest",
        search_objective=search_objective,
        client_scope={
            "platform": client_profile.platform,
            "markets": client_profile.markets,
            "categories": client_profile.categories,
            "trend_definition": client_profile.trend_definition,
            "query": keyword,
        },
        candidates=candidates,
        extraction_warnings=warnings,
        excluded_items=excluded,
        raw_response_path=raw_response_path,
    )
