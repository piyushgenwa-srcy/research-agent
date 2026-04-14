# Skill: Market Assortment Intake

## Classification
**Type:** Skill (LLM reasoning + structured extraction)
**Use this skill when:** The agent needs to turn retailer/category-page inputs into structured market-coverage context
**Input:** Retailer/storefront URLs, scraped product lists, category pages, or notes describing current assortment
**Creates or refines artifact:** `market_assortment_context`

---

## Role
Convert raw competitor assortment inputs into a reusable market-context object. This is not a trend-discovery step and not a recommendation step. It answers a narrower question first:

"What do target retailers already carry, how is that assortment clustered, and where are the credible whitespace opportunities or under-covered formats?"

Use this skill when the PM provides store/category URLs such as Rappi retailer pages and wants the workflow to reason from current market coverage before profiling the customer or generating recommendations.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| `retailer_inputs` | PM / scraper / manual collection | URLs, product page exports, category screenshots, or notes |
| `target_platform` | PM or inferred | Usually `rappi`, but can be any commerce surface |
| `target_markets` | PM or inferred | e.g. `["MX"]` |
| `focus_categories` | PM or inferred | e.g. beauty, supplements, electronics |

---

## Working Style

Think like a category strategist building the context pack for a later recommendation engine:
- inventory what is present before judging what is missing
- distinguish broad category presence from true assortment depth
- identify whitespace carefully; "few products observed" is not automatically a gap
- preserve retailer differences instead of averaging them away

Do not claim demand, sales velocity, or product trend status here. This skill is only about current market coverage and observed assortment structure.

---

## Reasoning Process

### Step 1 - Normalize retailer inputs
For every URL or source item, capture:
- retailer name
- platform
- category page or store page
- category inferred from URL or content
- whether the source is a full category page, a subcategory page, or a storefront root

If some URLs are malformed or duplicated, normalize them and keep a warning log.

### Step 2 - Extract what each retailer is currently selling
From each page or source payload, identify:
- product titles as shown
- normalized product formats
- brand names when visible
- observed price bands when visible
- subcategory patterns such as sun care, acne care, lip makeup, supplements, etc.

Collapse obvious duplicates but do not over-merge distinct formats.

### Step 3 - Build category coverage by retailer
For each retailer, summarize:
- which categories/subcategories are clearly present
- whether the assortment looks broad, narrow, premium-skewed, mass-skewed, or specialist
- where the retailer appears heavy on branded staples versus generic or emerging formats

### Step 4 - Identify cross-retailer gaps and whitespace
Across all retailers, look for:
- subcategories with repeated consumer need but weak observed coverage
- product formats that appear only once or only in specialist stores
- over-indexed areas where recommendations should be deprioritized unless differentiation is strong
- assortment holes by retailer archetype, such as pharmacy-heavy assortment but weak trend-led beauty accessories

Classify each gap carefully:
- `coverage_gap`: little or no observed assortment across the set
- `depth_gap`: category exists, but assortment is shallow
- `format_gap`: demand cluster exists, but the specific format is missing
- `retailer_gap`: one retailer type is under-covered relative to others

### Step 5 - Translate findings into downstream planning signals
Produce planning signals that later skills can use:
- priority subcategories to search harder in trend discovery
- deprioritized saturated formats
- retailer archetypes to benchmark against
- hypotheses for sourcing recommendations

These are hypotheses, not final recommendations.

### Step 6 - Output the structured market context

```json
{
  "platform": "rappi",
  "markets": ["MX"],
  "focus_categories": ["beauty", "supplements"],
  "retailers": [
    {
      "retailer_name": "Farmacias Guadalajara",
      "store_url": "string",
      "observed_categories": ["dermocosmetica", "cuidado de la piel", "cuidado del cabello"],
      "assortment_profile": "pharmacy-led, dermocosmetic heavy, branded skincare staple assortment",
      "observed_formats": ["snail mucin serum", "anti-acne gel", "hair loss shampoo"],
      "coverage_notes": "strong on treatment skincare, weaker on accessories and trend-led formats"
    }
  ],
  "category_summary": [
    {
      "category": "beauty",
      "observed_subcategories": ["dermocosmetica", "skin care", "hair care", "makeup", "nails"],
      "saturated_formats": ["basic facial cleansers", "mass-market shampoo"],
      "undercovered_formats": ["travel-size impulse beauty", "beauty tools", "trend-led treatment hybrids"],
      "market_note": "coverage broad in staples, thinner in novelty and convenience-led formats"
    }
  ],
  "gap_hypotheses": [
    {
      "gap_type": "format_gap",
      "category": "beauty",
      "gap_name": "impulse-priced beauty tools",
      "evidence": "observed broad skincare and makeup coverage but limited beauty accessory depth outside specialist retailers",
      "confidence": "MEDIUM"
    }
  ],
  "search_priorities": {
    "prioritize": ["beauty accessories", "travel-size treatments", "trend-led hair care"],
    "deprioritize": ["commodity cleansers", "commodity shampoo"],
    "benchmark_retailers": ["Farmacias Guadalajara", "Sally Beauty", "specialist dermocosmetic stores"]
  },
  "warnings": ["duplicate URL normalized", "some pages were storefront roots with limited category detail"]
}
```

---

## Guardrails

- **Do not infer demand from shelf presence alone.** Presence means availability, not velocity.
- **Do not overstate gaps.** A missing format across a small retailer sample is only a hypothesis.
- **Keep category logic generic enough for sourcing.** Normalize branded assortment into sourceable formats where possible.
- **Preserve retailer asymmetry.** If pharmacies look saturated and indie beauty stores do not, record that distinction.
- **Log thin evidence.** If a category page is sparse or partially loaded, lower confidence and say so.

---

## Orchestration Notes

This skill does not decide what runs next. The harness may use the resulting `market_assortment_context` to:
- enrich `client_profile`
- sharpen extraction and synthesis focus
- ground assortment-fit judgments later in the run

Use this skill whenever retailer/category inputs materially improve the agent's view of current shelf coverage.
