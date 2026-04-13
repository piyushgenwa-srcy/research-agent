# Skill: Demand Tier Classification

## Classification
**Type:** Skill (LLM reasoning with calibrated thresholds)
**Called:** Once per candidate product
**Calibrated against:** NocNoc research run, April 2026 (25+ products)

---

## Role
Combine trend score, marketplace saturation, social signal strength, and gross margin into a demand tier assignment. Classify each product as Tier 1, Tier 2, Tier 3, or Skip. Flag conflicting signals for PM review rather than auto-resolving.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| `trend_score` | SerpAPI → Google Trends, 5yr weekly avg | geo = client target markets |
| `ml_listing_count` | Oxylab → listado.mercadolibre.com.mx/{slug} | Parse "total" from embedded JSON |
| `social_signal_strength` | Skill 02 output | HIGH / MEDIUM / LOW from trend discovery |
| `sourcing_price` | TMAPI → AliExpress / CJDropshipping | USD per unit, MOQ=1; flagged if proxy |
| `retail_price_comp` | Oxylab → ML MX comps | Estimated retail in target market |
| `client_profile` | Skill 00 | Adjusts thresholds for Rappi ops items |

---

## Thresholds (Calibrated)

### ML Listing Count (Saturation)
| Count | Label |
|---|---|
| < 200 | Low — opportunity |
| 200–600 | Moderate — opportunity with differentiation |
| 600–1,500 | High — harder to enter, needs strong USP |
| > 1,500 | Saturated — skip |

### Google Trends Signal (5yr weekly avg, geo=target market)
| Score | Label |
|---|---|
| ≥ 30 | Strong |
| 20–29 | Viable |
| 10–19 | Weak — borderline |
| < 10 | Insufficient — drop |

### Gross Margin Floor
| Use case | Minimum gross margin |
|---|---|
| Standard (Rappi / Meli) | 40% |
| Preferred | > 55% |

Gross margin = (retail_price_comp − sourcing_price) / retail_price_comp

---

## Tier Rules

**Tier 1 — Strong opportunity**
- Trend score ≥ 20 AND social_signal = HIGH
- AND ml_listing_count < 600
- AND gross margin > 55%
- Confidence: HIGH

**Tier 2 — Good opportunity**
- Trend score ≥ 20 (or social_signal = MEDIUM with trend score ≥ 15)
- AND ml_listing_count 200–1,500
- AND gross margin 40–55%
- Confidence: MEDIUM

**Tier 3 — Conditional**
- Trend score 10–19 OR social_signal = LOW
- OR seasonal signal only (spike in specific months, low otherwise)
- OR platform-specific fit caveat (e.g., works for Meli but not Rappi due to delivery constraints)
- Confidence: LOW
- Must include condition note (e.g., "Q4 only", "Meli only — not Rappi-deliverable")

**Skip**
- Trend score < 10 in all target markets
- OR ml_listing_count > 1,500
- OR gross margin < 40%
- OR time_machine status = CLOSED (product already saturated in LatAM)

---

## Client Adjustments

**Rappi — operational items exception:**
Operational/warehouse items (delivery bags, packaging, warehouse supplies) do not require trend signal. For these:
- Skip trend_score threshold check
- Apply only: margin floor (> 40%) + sourcing feasibility (MOQ achievable)
- Classify as Tier 2 by default if operationally fit; Tier 1 if strong client demand signal exists

**Meli — fashion small-batch model:**
For Meli private label, lower the confidence threshold slightly — small batch (20–50 units) means lower risk per SKU:
- Tier 3 items with strong sentiment opportunity (from skill 05) can be promoted to "Tier 3 — test batch recommended" rather than dropped

---

## Conflict Rule

If a product has **OPEN trend + HIGH social signal** but **ml_listing_count > 1,500**:
- Do NOT auto-assign Skip
- Flag as `conflict: true` with note: "Strong demand signal but high saturation — assess if differentiation (private label, unique format) can break in"
- Escalate to PM with both data points visible

---

## Output

```json
{
  "product_name": "string",
  "tier": "1 | 2 | 3 | Skip",
  "confidence": "HIGH | MEDIUM | LOW",
  "conflict": false,
  "conflict_note": "null or explanation",
  "condition_note": "null or e.g. 'Q4 only', 'Meli only'",
  "data": {
    "trend_score": 45,
    "trend_score_geo": "MX",
    "ml_listing_count": 128,
    "ml_slug_used": "string",
    "sourcing_price_usd": 4.50,
    "sourcing_price_method": "TMAPI | proxy",
    "retail_price_comp_usd": 18.00,
    "gross_margin_pct": 75
  }
}
```

---

## Guardrails

- **Never invent a sourcing price.** If TMAPI is unavailable, use Amazon US retail × 0.30 as proxy and flag `sourcing_price_method: proxy`. Do not leave field blank.
- **Log the ML slug used.** Slug selection affects listing count. Always record which slug returned the result for auditability.
- **If ML returns 0 listings:** Retry with 2 alternate slug variations before treating as 0. If still 0 after retries, note `ml_listing_count: 0 (verified — near-zero saturation)` — this is often Tier 1.
- **Missing trend data:** If SerpAPI returns no data for a market, do not default trend_score to 0. Flag as `trend_score: null` and demote to Tier 3 maximum (cannot confirm Tier 1/2 without trend data).
- **Gross margin is gross only.** Does not include ML commission (~13–20%), payment processing (~3%), shipping, or returns. Net margin ≈ gross margin − 18–22%.
