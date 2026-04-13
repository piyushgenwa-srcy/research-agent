# Skill: Catalog Assembly

## Classification
**Type:** Skill (LLM reasoning)
**Called:** Once, after all products are tiered
**Branches by:** `client_profile.output_mode`

---

## Role
Group tiered products into coherent catalogs or dashboard-ready output. The format, structure, and grouping logic differs by client. This is the final assembly step — inputs are fully validated, tiered, and enriched. Do not re-classify or re-score products here.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| `tiered_products` | Skill 06 output (all products) | With tier, confidence, conflict flags |
| `sku_definitions` | Skill 04 output (all products) | With SKU specs and sourcing details |
| `sentiment_data` | Skill 05 output (Meli only) | Likes, complaints, product opportunities |
| `client_profile` | Skill 00 | Determines output mode and catalog structure |

---

## Rappi Mode (`output_mode = catalog`)

### Catalog Structure
Assemble **3 catalogs**:

1. **Quick Commerce High-Margin** — Tier 1 + Tier 2 products from beauty, electronics, toys, sports, supplements, unique brands
2. **Operational / Warehouse** — All operational items regardless of tier (delivery bags, packaging, restaurant supplies, aluminium can machines)
3. **Emerging / Unique Brands** — Tier 1 + Tier 2 products with `time_machine: true` and strong originality signal

### Per Product Entry (Rappi)
Each catalog entry includes:
- Product name
- SKU spec (from skill 04)
- Tier + confidence
- Gross margin %
- Sourcing price (USD)
- Retail price estimate (USD)
- MOQ
- Shipping note (Mexico City)
- Last-mile fit flag (Rappi-deliverable: yes/no + note if no)
- Source (AliExpress / CJDropshipping / Factory)

### Sorting
Within each catalog: sort by tier (1 → 2 → 3), then by gross margin descending.

### Format
Structured markdown file. One catalog per section (`## Catalog 1 — Quick Commerce High-Margin`). Summary table at top of each catalog.

---

## Meli Mode (`output_mode = dashboard`)

### Catalog Structure
Assemble **by category assortment**:
- Group products by `client_profile.categories` (e.g., Dresses, Athleisure, Casual Wear, Beachwear)
- Within each category: organize as assortment — cover different use cases/silhouettes/occasions (not just variants of one SKU)

### Per Product Card (Meli)
Each product card includes:
- Product name + trend source (which TikTok/IG/RED signal it came from)
- Tier + confidence
- SKU spec (from skill 04) — 2–3 variants
- Differentiation angle (private label / white label)
- Sentiment insight summary — key like, top complaint, product opportunity
- Shein-style batch recommendation: "Start with [N] units across [X] variants for test batch"
- Gross margin %
- Sourcing price (USD)
- Retail price estimate (MX + BR if available)
- ML listing count (saturation check)

### Trend → Product → Assortment Pipeline
For each category, write a 2–3 sentence mapping:
"[Trend signal] → [Specific SKUs] → [Assortment role]"
Example: "Y2K mini dress viral on TikTok US (avg 2.3M views/post) → bodycon stretch mini in 4 colorways → entry-level occasion piece in the Dresses assortment."

This is the explicit mapping Meli requested — must be present for every product card.

### Dashboard JSON Output
In addition to Notion summary, generate structured JSON per product card for dashboard ingestion:

```json
{
  "product_id": "string",
  "category": "dresses",
  "tier": "1",
  "confidence": "HIGH",
  "trend_source": { "lane": "tiktok", "signal_strength": "HIGH", "evidence": "..." },
  "time_machine": true,
  "sku_variants": [...],
  "differentiation_angle": "string",
  "sentiment": {
    "top_like": "string",
    "top_complaint": "string",
    "product_opportunity": "string"
  },
  "batch_recommendation": "20 units across 4 colorways",
  "gross_margin_pct": 68,
  "sourcing_price_usd": 7.50,
  "retail_price_usd": 23.00,
  "ml_listing_count": 95,
  "trend_to_product_mapping": "string"
}
```

---

## Shared Rules (Both Modes)

- **Skip products stay out.** Never include Skip-tiered products in any catalog. If PM wants to review them, they go in a separate "Flagged / Below Threshold" appendix only.
- **Conflict-flagged products get their own section.** Do not bury conflicting signals. Group them in a "Needs PM Decision" callout at the end of the catalog.
- **Minimum catalog size.** If any catalog has fewer than `client_profile.min_products` products, flag it. Do not pad with Skip-tier products to hit the number.
- **Proxy pricing must be visible.** Any product where `sourcing_price_method = proxy` gets a footnote: "Sourcing price estimated — verify before ordering."
- **Do not rewrite the tier.** Catalog assembly is grouping and formatting only. Do not upgrade or downgrade tiers here.

---

## Output Files

**Rappi:**
- `catalog_rappi_[date].md` — 3 catalogs in structured markdown

**Meli:**
- `catalog_meli_[date].md` — Notion-ready markdown with assortment structure
- `catalog_meli_[date].json` — Dashboard-ready JSON array of product cards
