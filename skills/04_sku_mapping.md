# Skill: Trend → SKU Mapping

## Classification
**Type:** Skill (LLM reasoning)
**Use this skill when:** The agent needs to convert a promising opportunity into concrete sourceable product formats or variants
**Creates or refines artifact:** `sku_definitions`

Use more selectively for pure sourcing clients where category-level opportunity is enough and concrete SKU specification would add little value.

---

## Role
Translate a trend signal into 2–3 specific, sourceable SKU definitions. This is the "concreteness" step — the bridge between "this product category is trending" and "here is the exact item to source." Output must be concrete enough that a sourcing team can search AliExpress or brief a factory without additional interpretation.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| `trend_item` | Working artifact | Single opportunity with lane evidence and score |
| `client_profile` | Skill 00 | See `00_client_profile.md` |

---

## Reasoning Process

### Step 1 — Identify the sourceable generic format
Strip brand names. Identify the product category and format that can be sourced generically.
- "COSRX snail mucin serum" → "96% snail secretion filtrate serum, 100ml, dropper bottle"
- "Shein Y2K mini dress TikTok trend" → "Stretch mini dress, bodycon cut, synthetic blend, sizes XS–XL"
- "Rappi delivery bag trend" → "Insulated delivery bag, 30L, waterproof exterior, Rappi-logo printable"

### Step 2 — Define key product attributes
For each SKU, specify:
- Dimensions / size range
- Materials / key ingredients (for beauty/supplements)
- Core feature (what makes it match the trend)
- Color/variant options
- Packaging format

### Step 3 — Generate 2–3 variants
Variants should cover the range of buyer entry points or use cases, not just size differences.
- Example (dresses): (1) casual midi — everyday wear, (2) occasion mini — nightout/event, (3) lounge maxi — comfort/home
- Example (beauty): (1) basic 30ml trial size, (2) full 100ml hero SKU, (3) set with complementary product
- Example (Rappi ops): (1) standard 30L delivery bag, (2) thermal insulated version, (3) branded with logo space

### Step 4 — Apply client use_case
- **Sourcing (Rappi):** Focus on functional fit, durability, MOQ feasibility (~50 pcs). No branding differentiation needed.
- **Private label (Meli):** Identify what differentiation is achievable — packaging redesign, minor formulation tweak, branding. Specify what the "white label ready" version looks like.
- **White label (Meli):** Identify existing supplier brands that will badge under Meli. Note if any regulatory step is needed (COFEPRIS for cosmetics, etc.).

### Step 5 — Flag sourcing constraints
- MOQ: is `client_profile.moq` achievable for this product format?
- Lead time estimate: standard (15–30 days AliExpress/CJ) or long (60+ days factory direct)
- Licensing risk: any IP, trademark, or regulatory concern for this format in target market?
- Fragility / last-mile fit (Rappi only): can this survive a motorbike courier delivery?

### Step 6 — Output per trend

```json
{
  "trend_name": "string",
  "skus": [
    {
      "sku_name": "string",
      "sku_description": "specific, sourceable product description",
      "key_attributes": {
        "dimensions": "...",
        "materials": "...",
        "core_feature": "...",
        "variants": ["color/size options"]
      },
      "differentiation_angle": "private label / white label / generic — and what the angle is",
      "moq_estimate": 50,
      "lead_time_estimate": "15–30 days",
      "sourcing_constraint_flags": ["list any flags"],
      "recommended_source": "AliExpress | CJDropshipping | Factory direct | TMAPI"
    }
  ]
}
```

---

## Guardrails

- **Never output a brand name as the SKU.** Always describe the generic format. Brand names can appear in evidence, not in the SKU definition.
- **Variants must be meaningfully different**, not just color swaps. Cover different buyer intents or use cases.
- **Rappi last-mile check is mandatory.** If the product cannot survive standard motorbike courier delivery (fragile glass, requires refrigeration, oversized), flag it and suggest a Rappi-compatible alternative format.
- **Meli private label must be realistic.** Do not propose differentiation that requires custom formulation or >90-day lead time for the first batch. Small batch = 20–50 units, fast iteration.
- **If MOQ is unachievable** at `client_profile.moq`, note the actual minimum and flag for PM review. Do not silently drop the product.
