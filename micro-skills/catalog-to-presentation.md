# Skill: catalog-to-presentation

## Purpose
Convert a `final_catalog.json` artifact into a self-contained HTML presentation deck for client delivery. The presentation prioritises product recommendations first, evidence second, methodology last. It must be beautiful, scannable, and ready to share without any tooling.

## When to invoke
After `final_catalog.json` has been written. Call `write_artifact` with filename `presentation.html` and a string content field (not a JSON object — write the full HTML as a JSON-escaped string under the key `"html"`). The harness will write it as-is.

## Input artifacts required
- `final_catalog.json` — primary source for all product data
- `tiered_recommendations.json` — scoring rationale and risk flags
- `client_profile.json` — for client name, markets, categories
- `run_gaps.md` — for confidence disclosures

## Output
Single self-contained `presentation.html` file — no external dependencies, all CSS and JS inlined. Must render correctly when opened directly in any modern browser.

## Slide structure (in order)

1. **Cover** — Client name, run date, categories, markets, "Private Label Sourcing Research"
2. **Executive Summary** — Total recommendations, tier breakdown (Tier 1/2/3 counts), lanes used, total evidence items reviewed, 1-sentence headline finding
3. **Data Confidence** — Which lanes produced data, which failed, what is inferred vs. empirical. Use a traffic-light indicator per lane.
4. **Tier 1 products** — One slide per Tier 1 product. Include: product name, composite score (large), executive summary, evidence strength bars (TikTok / Amazon / MercadoLibre), SKU table with pricing in both MXN and USD, differentiation spec, key risk, recommended action.
5. **Tier 2 products** — One slide showing all Tier 2 products as cards with score, category, 1-line rationale, recommended action.
6. **Tier 3 / Monitor** — Brief table with product, score, why deprioritised.
7. **Collection Strategy** — Two columns: home collection and fashion collection. For each: collection name, products in it, positioning line, cross-sell logic.
8. **Next Steps** — Numbered action items with priority. Pull from `recommended_next_steps` across Tier 1 products first.
9. **Methodology & Limitations** — Scoring weights, evidence volume (candidates reviewed / usable), known limitations. Keep honest but not prominent.

## Design rules

### Visual hierarchy
- Product name and composite score are always the largest elements on a product slide
- Evidence strength is always visualised (bars or icons), never text-only
- Pricing is always shown in both MXN and USD
- Tier 1 gets full-bleed individual slides; Tier 2 gets card grid; Tier 3 gets table row

### Colour palette
Use the client's brand palette when inferable from `client_profile.json` platform field:
- `mercadolibre`: background `#1A1A2E`, accent `#FFE600`, secondary `#00A650`, text `#F0F0F0`
- `rappi`: background `#1A1A1A`, accent `#FF441B`, secondary `#FFDE00`, text `#F5F5F5`
- default: background `#0F172A`, accent `#6366F1`, secondary `#22D3EE`, text `#F1F5F9`

### Typography
- Headlines: bold, 2.5–4rem
- Body: 0.95–1.1rem, line-height 1.6
- Scores: 4–6rem, accent colour, bold
- All text must pass WCAG AA contrast on its background

### Navigation
- Arrow key and click navigation between slides
- Slide counter (current / total) always visible
- Keyboard shortcut hint on first slide

### Confidence signals
- Any data point from a failed lane (e.g. ML parser failure) must show a `[inferred]` badge in amber
- Any MXN price that is a conversion estimate must show `~MXN` prefix
- Tier confidence penalty note must appear on every product slide as a small footnote

## Anti-patterns
- Do not show raw JSON field names to the client
- Do not include methodology slides before product slides
- Do not hide data gaps — surface them clearly but briefly
- Do not use more than 3 font sizes on a single slide
- Do not include more than 7 bullet points on any slide
