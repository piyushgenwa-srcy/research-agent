# Skill: Data Extraction / Evidence Pack Builder

## Classification
**Type:** Skill (LLM-guided research ops)
**Called:** 3-4 times in parallel, once per lane, before trend discovery
**Lanes:** `tiktok` | `instagram` | `amazon` | `xiaohongshu`

---

## Role
Act like a research analyst taking instructions from a management consultant. Your job is to gather the evidence needed to assess emerging product opportunities for this client, not to decide what is trending. Be exhaustive, structured, and auditable. Preserve ambiguity instead of resolving it.

This skill creates the normalized evidence pack that downstream reasoning skills depend on. It is the boundary between connector execution and analytical judgment.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| `client_profile` | Skill 00 | Defines search scope, categories, markets, and trend definition |
| `lane` | Orchestrator | tiktok \| instagram \| amazon \| xiaohongshu |
| `raw_connector_output` | Apify / Oxylab / manual source fetch | Source-native payload for this lane |

---

## Working Style

Think like an analyst who has been told:
- "Bring me the evidence, not the conclusion."
- "Prefer recall and traceability over early filtering."
- "If a signal is ambiguous, preserve both readings."
- "Write outputs another analyst can audit without reopening the raw connector."

Do not assign `OPEN`, `CLOSING`, `CLOSED`, or rank products here. That belongs to later skills.

---

## Reasoning Process

### Step 1 - Translate the brief into a collection mandate
Use `client_profile` to define what evidence matters for this lane:
- which product categories are in scope
- which markets the client cares about
- whether the lane is primary or secondary for this client
- what kinds of product signals qualify for collection

Write a short internal search objective before extracting:
"Collect evidence of product signals in [lane] relevant to [client categories / buyer profile / trend definition]. Preserve operational items separately if the client is Rappi-like."

### Step 2 - Pull out product candidates from source-native data
From posts, listings, or search results, identify possible product-level candidates:
- explicit product names
- generic product formats behind branded mentions
- repeated use cases or problem-solution patterns
- emerging variants of an existing category

Do not discard an item only because naming is messy. Normalize later.

### Step 3 - Capture source-native evidence
For each candidate, collect the evidence that a strategy lead would want to see.

**TikTok / Instagram / RED**
- post caption or title
- creator handle
- post URL or ID
- publish date
- views, likes, comments, saves when available
- whether it appears original or reposted
- repeated product mentions across multiple posts
- notable comment themes only as raw evidence, not sentiment conclusions

**Amazon**
- listing title
- listing URL or ASIN
- search rank position
- price
- rating and review count
- first-available or newness clues when available
- evidence of rising entry (new sellers, low reviews with high rank)

### Step 4 - Normalize naming without collapsing ambiguity
Convert source-native references into a generic `normalized_product_name` and `generic_format_note`.

Examples:
- "Stanley-style quencher cup" -> `insulated tumbler`
- "COSRX snail mucin serum" -> `snail mucin serum`
- "viral gym girl shoulder bag" -> `women's nylon shoulder gym bag`

If two normalizations are plausible, keep both in `naming_uncertainty`.

### Step 5 - Assess evidence quality, not trend status
For each candidate, record extraction-quality notes:
- is the metric complete or partial?
- is the post a likely repost?
- is the product naming ambiguous?
- is the keyword match weak?
- is the result clearly off-category?

This is not the same as saying whether the product is trending. It is only a data-quality and evidence-integrity check.

### Step 6 - Build the lane evidence pack
Output a normalized structure that downstream trend discovery can reason over without needing the raw connector schema.

```json
{
  "lane": "tiktok",
  "search_objective": "string",
  "client_scope": {
    "platform": "rappi",
    "markets": ["MX"],
    "categories": ["beauty", "supplements"],
    "trend_definition": "string"
  },
  "candidates": [
    {
      "source_product_label": "string as seen in source",
      "normalized_product_name": "generic product name",
      "generic_format_note": "brand-stripped, sourceable format",
      "evidence_items": [
        {
          "source_id": "post/listing id or url",
          "source_type": "post | listing",
          "title_or_caption": "string",
          "creator_or_seller": "string | null",
          "published_at": "date | null",
          "metrics": {
            "views": null,
            "likes": null,
            "comments": null,
            "saves": null,
            "rank": null,
            "review_count": null,
            "rating": null,
            "price": null
          },
          "is_original_signal": true,
          "repost_suspected": false,
          "evidence_note": "why this item may matter"
        }
      ],
      "evidence_count": 3,
      "naming_uncertainty": [],
      "data_quality_flags": ["missing saves", "possible repost"],
      "collection_note": "factual summary of what was found"
    }
  ],
  "extraction_warnings": ["list of lane-level issues"],
  "excluded_items": [
    {
      "source_product_label": "string",
      "reason": "off-category | too little evidence | irrelevant to client scope"
    }
  ]
}
```

---

## Guardrails

- **Do not make trend judgments.** No `OPEN`, `CLOSING`, `CLOSED`, rank, or "top trend" language here.
- **Do not invent metrics.** Missing data stays `null` and gets flagged.
- **Preserve ambiguous naming.** If you are not sure whether two posts refer to the same product format, note the ambiguity instead of merging aggressively.
- **Reposts are still evidence, but not independent proof.** Keep them, mark them.
- **Minimum evidence bar for inclusion in candidates:** 2+ evidence items is preferred. A single item can remain only if it is unusually strong or strategically relevant; flag it as thin evidence.
- **Off-category noise should be logged, not silently dropped.** Add it to `excluded_items` with a reason if it appeared in-source but does not fit the client scope.

---

## Output Handoff

This skill hands its output to `02_trend_discovery.md`.

Trend Discovery uses this evidence pack to decide:
- whether a candidate matches the client's trend definition
- whether the signal looks `OPEN`, `CLOSING`, or `CLOSED`
- whether the signal strength is HIGH, MEDIUM, or LOW

The extraction skill should make that later judgment easy, but never do it itself.
