# Skill: Sentiment Analysis → Product Opportunity

## Classification
**Type:** Skill (LLM reasoning)
**Called:** Once per trend item (Meli only)
**Skip when:** `client_profile.use_case = sourcing` OR `platform = rappi` — skip for any client that is sourcing existing products rather than designing new ones. Sentiment analysis only adds value when the client can act on product design feedback (private label, white label). NocNoc = skip. Rappi = skip. Meli = run.

---

## Role
Extract what buyers like and complain about from social posts and reviews for a given trend. Convert complaints and wishlist signals into concrete product improvement opportunities. This feeds the consumer insight layer Meli needs to translate trend data into actionable SKU differentiation.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| `raw_comments` | Apify TikTok/IG comments + Amazon reviews | Comments and reviews for posts/products matching this trend |
| `trend_item` | Skill 03 output | The trend being analyzed |
| `client_profile` | Skill 00 | Must be `platform = mercadolibre` |

---

## Reasoning Process

### Step 1 — Categorize comments into 3 buckets

**Likes** — what users consistently praise:
- Specific features ("the fabric feels so soft")
- Aesthetic attributes ("the color is exactly like the photos")
- Use case fit ("perfect for beach trips")

**Complaints** — what users consistently criticize:
- Product failures ("strap broke after one wear")
- Fit/sizing issues ("runs 2 sizes small, order up")
- Quality gaps ("looks cheap in person, not like TikTok video")
- Fulfillment issues ("arrived in 3 weeks" — note but deprioritize, this is logistics not product)

**Wishlists** — features users explicitly request:
- "I wish it came in plus sizes"
- "Would be perfect with pockets"
- "Need a longer version of this"

### Step 2 — Identify addressable gaps
For each complaint or wishlist signal: is this gap addressable via product design (sourcing decision, private label spec)?

- "Strap broke" → specify reinforced strap in SKU attributes → addressable
- "Runs small" → size up in order recommendation OR spec true-to-size → addressable
- "Took 3 weeks to ship" → logistics, not product → not addressable via SKU, skip
- "Wish it had pockets" → spec pockets in private label design → addressable

### Step 3 — Generate product opportunity statements
For each addressable gap, generate a 1–2 sentence product opportunity:

Format: "Buyers love [X] but consistently complain about [Y]. A private label version that [specific fix] would capture this demand gap."

Examples:
- "Buyers love the Y2K aesthetic and color options but complain straps break quickly. A private label version with reinforced spaghetti straps and the same colorways captures this exact gap."
- "TikTok viewers love the silhouette but 40% of comments mention it runs 2 sizes small. Spec true-to-size sizing in the factory brief and call it out in the product title."

### Step 4 — Fashion-specific signals (Meli categories)
For women's fashion trends, also extract:
- **Color trends**: what specific colors/palettes appear most in liked posts
- **Silhouette preferences**: midi vs mini vs maxi, fitted vs flowy, neckline preferences
- **Fabric complaints**: what fabric attributes get complaints (scratchy, see-through, cheap-looking)
- **Occasion signals**: what events buyers mention wearing the item to (work, beach, date, lounge)

### Step 5 — Output

```json
{
  "trend_name": "string",
  "sentiment_summary": {
    "likes": ["top 3–5 consistent positive signals"],
    "complaints": ["top 3–5 consistent negative signals"],
    "wishlists": ["top 2–3 explicit feature requests"]
  },
  "product_opportunities": [
    {
      "gap": "specific complaint or wishlist",
      "addressable": true,
      "opportunity_statement": "1–2 sentence product opportunity",
      "sku_implication": "what to specify differently in SKU attributes"
    }
  ],
  "fashion_signals": {
    "trending_colors": ["list"],
    "preferred_silhouettes": ["list"],
    "fabric_complaints": ["list"],
    "occasion_signals": ["list"]
  }
}
```

---

## Guardrails

- **Only pass addressable gaps to SKU Mapping.** Logistics complaints, payment issues, and platform experience issues are not product opportunities — exclude from `product_opportunities`.
- **Minimum evidence bar:** A complaint must appear in at least 5% of comments or be mentioned explicitly by 3+ independent reviewers to qualify as a signal. One-off complaints → discard.
- **Do not moralize or editorialize.** Report what buyers say, not what they "should" want. If buyers love a fast-fashion item despite quality concerns, that's the signal.
- **Meli-specific:** Fashion signals (color, silhouette, fabric, occasion) must be extracted for every Meli trend. These directly feed the private label brief.
- **Skip for Rappi entirely.** Rappi's use case is operational sourcing, not consumer sentiment-driven private label. Do not call this skill for `platform = rappi`.
