"""Haiku-4.5 comment classifier for richer demand-signal extraction.

Replaces regex-only classification with a structured LLM pass.
Falls back to the regex classifier if the Anthropic package is not
installed or no API key is supplied.

Classification schema per comment
----------------------------------
themes : List[str]
    One or more of: want_to_buy, size_query, complaint, compliment,
    price_sensitivity, shipping_concern, restock_request, other.
sentiment : "positive" | "negative" | "neutral"
purchase_intent_score : 0.0–1.0
    How likely the commenter would buy / is actively shopping.
key_phrase : str | None
    The most signal-rich 1–5 word fragment.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

_WANT_TO_BUY = re.compile(
    r"\b(where|dónde|donde|link|comprar|buy|quiero|want|need|necesito|precio|price|how much|cuánto|cuanto)\b",
    re.IGNORECASE,
)
_SIZE_QUERY = re.compile(
    r"\b(talla|size|medida|xs|sm|xl|xxl|fit|talle|grande|pequeño|pequeno|ancho|largo)\b",
    re.IGNORECASE,
)
_COMPLAINT = re.compile(
    r"\b(bad|malo|mala|roto|rota|ugly|feo|fea|cheap|barato|dura|thin|delgado|see.through|transparente|wrong|equivocado|devolver|return|refund|reembolso|decepcio|disappoint)\b",
    re.IGNORECASE,
)
_COMPLIMENT = re.compile(
    r"\b(beautiful|hermoso|hermosa|lindo|linda|gorgeous|love|amo|encanta|perfect|perfecto|gorgeous|precioso|preciosa|cute|bonito|bonita|amazing|increíble)\b",
    re.IGNORECASE,
)
_PRICE_SENSITIVE = re.compile(
    r"\b(caro|expensive|precio|cuánto cuesta|cuanto vale|muy caro|affordable|barato|discount|oferta|descuento)\b",
    re.IGNORECASE,
)


def classify_comment_regex(text: str) -> Dict[str, Any]:
    """Fast regex-based fallback classifier. Returns the same schema as the LLM version."""
    themes = []
    if _WANT_TO_BUY.search(text):
        themes.append("want_to_buy")
    if _SIZE_QUERY.search(text):
        themes.append("size_query")
    if _COMPLAINT.search(text):
        themes.append("complaint")
    if _COMPLIMENT.search(text):
        themes.append("compliment")
    if _PRICE_SENSITIVE.search(text):
        themes.append("price_sensitivity")
    if not themes:
        themes = ["other"]

    has_complaint = "complaint" in themes
    has_compliment = "compliment" in themes
    if has_complaint and not has_compliment:
        sentiment = "negative"
    elif has_compliment and not has_complaint:
        sentiment = "positive"
    else:
        sentiment = "neutral"

    purchase_intent = 0.8 if "want_to_buy" in themes else (0.4 if "size_query" in themes else 0.1)

    return {
        "themes": themes,
        "sentiment": sentiment,
        "purchase_intent_score": purchase_intent,
        "key_phrase": None,
        "classifier": "regex",
    }


_CLASSIFICATION_PROMPT = """\
You are a social commerce analyst. Classify the following {n} comments from a fashion TikTok video.
{context}

Return ONLY a JSON array with one object per comment, in the same order.
Each object must have exactly these fields:
- "themes": list of strings from [want_to_buy, size_query, complaint, compliment, price_sensitivity, shipping_concern, restock_request, other]
- "sentiment": one of "positive", "negative", "neutral"
- "purchase_intent_score": float 0.0-1.0 (how likely this commenter is actively shopping)
- "key_phrase": the most signal-rich 1-5 word fragment, or null

Comments:
{comments_json}

Respond with only the JSON array, no explanation."""


def classify_comments_llm(
    comments: List[str],
    api_key: str,
    product_context: str = "",
    batch_size: int = 25,
) -> List[Dict[str, Any]]:
    """Classify comments using Haiku 4.5.

    Falls back per-comment to regex on any parse error.

    Args:
        comments:        Raw comment text strings.
        api_key:         Anthropic API key.
        product_context: Optional product/category context injected into the prompt.
        batch_size:      Comments per API call (default 25, ~$0.003/call at Haiku pricing).

    Returns:
        List of classification dicts in the same order as ``comments``.
    """
    try:
        import anthropic as _anthropic
    except ImportError:
        return [classify_comment_regex(c) for c in comments]

    client = _anthropic.Anthropic(api_key=api_key)
    results: List[Dict[str, Any]] = []

    for batch_start in range(0, len(comments), batch_size):
        batch = comments[batch_start: batch_start + batch_size]
        context_line = f"Product context: {product_context}\n" if product_context else ""
        prompt = _CLASSIFICATION_PROMPT.format(
            n=len(batch),
            context=context_line,
            comments_json=json.dumps(batch, ensure_ascii=False),
        )
        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = re.sub(r"^```[^\n]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            parsed: List[Dict[str, Any]] = json.loads(raw)
            if len(parsed) != len(batch):
                raise ValueError(f"Length mismatch: got {len(parsed)}, expected {len(batch)}")
            for item in parsed:
                item["classifier"] = "haiku"
            results.extend(parsed)
        except Exception:
            # Fallback: classify the whole batch with regex
            for text in batch:
                results.append(classify_comment_regex(text))

    return results


def classify_comments(
    comments: List[str],
    anthropic_api_key: Optional[str] = None,
    product_context: str = "",
) -> List[Dict[str, Any]]:
    """Public entry point. Uses Haiku if API key available, else regex.

    Args:
        comments:            List of raw comment text strings.
        anthropic_api_key:   If provided, uses Haiku 4.5; else falls back to regex.
        product_context:     Optional product/category context for the LLM.

    Returns:
        List of classification dicts.
    """
    if anthropic_api_key:
        return classify_comments_llm(comments, anthropic_api_key, product_context)
    return [classify_comment_regex(c) for c in comments]
