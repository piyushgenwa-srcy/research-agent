# Skill: Trend Synthesis + Time Machine Filter

## Classification
**Type:** Skill (LLM reasoning)
**Use this skill when:** The agent needs a unified cross-lane view of candidate opportunities
**Creates or refines artifact:** `trend_candidates`

---

## Role
Combine signals from multiple lanes into a unified, ranked trend list. Apply the time machine filter (US/China → LatAM). Apply client-specific fit filter. Produce a ranked opportunity view the harness can use for tiering, SKU concretization, or further evidence gathering.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| `lane_outputs` | Skill 02 (all lanes) | Array of signal lists, one per lane |
| `client_profile` | Skill 00 | See `00_client_profile.md` |
| `market_assortment_context` | Skill 00a / embedded in client_profile.market_context | Optional competitor coverage and whitespace context |

---

## Reasoning Process

### Step 1 — Deduplication
Match signals across lanes that refer to the same product (by name, function, or clear synonym). Merge into one unified signal record. Retain per-lane evidence.

### Step 2 — Multi-lane scoring
Score each unified signal using weighted lane contribution:

| Lane | Weight |
|---|---|
| TikTok | 0.50 |
| Instagram (original only) | 0.20 |
| Amazon | 0.20 |
| Xiaohongshu (Meli only) | 0.10 |

Signal strength multiplier: HIGH = 1.0, MEDIUM = 0.7, LOW = 0.3

`combined_score = Σ (lane_weight × strength_multiplier)` for all lanes where signal exists.

### Step 3 — Time machine filter
For each signal, assess: **"Is this product already trending in US/China but not yet available in the client's LatAM target markets?"**

- If yes → `time_machine: true`, apply 1.5× multiplier to combined_score
- Time machine lag estimate: TikTok US → LatAM = 6–12 months; Xiaohongshu → LatAM = 9–18 months
- If product is already well-known in LatAM (CLOSED status from lane data) → `time_machine: false`, no multiplier

### Step 4 — Client-specific fit filter
Apply `client_profile` to filter out trends that don't match this client's context:

**Rappi filter:**
- Keep: deliverable in minutes (not fragile, not oversized), impulse-purchase price point, fits quick commerce categories
- Keep: operational/warehouse items regardless of trend signal (these are utility sourcing, not trend-driven)
- Drop: slow-browsing products, high-consideration purchases, items requiring installation or setup

**Meli filter:**
- Keep: fashion/aspirational, private-label or white-label translatable, searchable on ML
- Keep: items that map to `client_profile.categories` (dresses, athleisure, etc.)
- Drop: pure operational/utility items, fast food, delivery supplies

### Step 5 - Assortment-whitespace adjustment
If `market_assortment_context` exists, evaluate each signal against observed retailer coverage:
- promote products that match a documented `coverage_gap`, `depth_gap`, `format_gap`, or `retailer_gap`
- penalize products that map to an already over-covered observed format unless the signal includes a clear novelty angle
- for Rappi or NocNoc sourcing, prefer products that improve category breadth rather than adding another commodity SKU to a crowded shelf

Add a short note:
- `assortment_fit_note`: why this signal helps fill a real shelf gap, or why it risks duplicating existing coverage

### Step 6 — Rank and trim
Sort surviving trends by: `final_score = combined_score × time_machine_multiplier`, then use assortment fit as a tie-breaker when scores are close.
Output top `client_profile.max_products` trends. Flag if fewer than `client_profile.min_products` survive all filters.

### Step 7 — Output per trend

```json
{
  "product_name": "string",
  "trend_status": "OPEN | CLOSING | CLOSED",
  "combined_score": 0.0,
  "time_machine": true,
  "time_machine_lag_estimate": "6–12 months",
  "final_score": 0.0,
  "assortment_fit": "positive | neutral | negative",
  "assortment_fit_note": "why this fills a real gap or duplicates existing coverage",
  "lane_evidence": {
    "tiktok": { "strength": "HIGH", "summary": "..." },
    "instagram": { "strength": "MEDIUM", "summary": "..." },
    "amazon": { "strength": "LOW", "summary": "..." }
  },
  "client_fit_note": "why this passes the client filter",
  "recommended_category": "string"
}
```

---

## Guardrails

- **Do not auto-resolve lane conflicts.** If TikTok says OPEN and Amazon says CLOSING, preserve both in `lane_evidence` and use the weighted score to decide rank — do not silently pick one.
- **Do not drop below min_products without flagging.** If fewer than `min_products` survive, flag the shortfall and explain which filter caused the most drop-off.
- **Instagram reposts from TikTok do not add score.** If tagged `repost_of_tiktok: true` in Skill 02 output, do not add Instagram lane weight for that signal — it is the same underlying signal.
- **Time machine flag is a signal multiplier, not a trump card.** A CLOSING trend with time_machine=true still ranks lower than an OPEN trend without it.
- **Do not hallucinate gaps.** Use assortment context only when retailer evidence actually supports a coverage view.
