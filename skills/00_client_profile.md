# Skill: Client Profile Parser

## Classification
**Type:** Skill (LLM reasoning)
**Called:** Once, at the start of every research run
**Input:** Raw client brief — any format (message, email, notes, bullet points)
**Output:** Structured `client_profile` JSON passed to all downstream skills

---

## Role
Transform an unstructured client description into the standardized `client_profile` object the rest of the pipeline depends on. The PM does not fill a form — they write naturally and this skill extracts structure from it. If required fields cannot be inferred, ask before proceeding.

---

## Inputs

| Input | Source | Format |
|---|---|---|
| `raw_brief` | PM | Any — Slack message, email, bullet notes, free text |

---

## Reasoning Process

### Step 1 — Read and extract
From the raw brief, extract every field you can infer with confidence. Use context clues:
- Platform name mentioned → `platform`
- Geography or "ship to" → `markets` + `ship_to`
- Product categories listed → `categories`
- Delivery speed, buyer type, use case → `buyer_profile`
- Words like "private label", "white label", "sourcing", "catalog" → `use_case` + `output_mode`
- MOQ mentioned or implied → `moq`
- Any mention of trend sources (TikTok, Xiaohongshu, 美团, Taobao) → `benchmark_sources`

### Step 2 — Infer where reasonable
Some fields can be inferred from platform context even if not stated:

| If platform is... | Default inferences |
|---|---|
| `rappi` | motivation = impulse, delivery_expectation = minutes, output_mode = catalog, use_case = sourcing |
| `mercadolibre` | motivation = aspirational, delivery_expectation = days, output_mode = dashboard |

Apply these defaults only when the brief doesn't contradict them.

### Step 3 — Write the trend_definition
This field cannot be defaulted — it must be specific to the client. Compose a 1–2 sentence definition from the brief:
- What kind of product qualifies as "trending" for this client?
- What sources are they watching (social, Chinese platforms, US market)?
- Are there any product types that are explicitly in or out?

### Step 4 — Identify missing required fields
Required fields: `platform`, `markets`, `categories`, `price_bracket`, `output_mode`, `use_case`

If any required field cannot be confidently inferred:
- Do NOT guess
- List the missing fields explicitly
- Ask the PM before generating the profile
- Format: "I can infer most of the profile, but need clarification on: [field] — [why it matters]"

### Step 5 — Determine which skills to run

Set `run_skills` based on the client's `use_case` and `output_mode`. This controls which steps the orchestrator executes.

| Skill | Always runs? | Skip when |
|---|---|---|
| 01 Data Extraction | Yes | Never |
| 02 Trend Discovery | Yes | Never |
| 03 Trend Synthesis | Yes | Never |
| 04 SKU Mapping | No | `use_case = sourcing` — client wants to source existing products, not define private/white label specs |
| 05 Sentiment Analysis | No | `use_case = sourcing` OR `platform = rappi` — only relevant when client needs product design input |
| 06 Demand Tier Classification | Yes | Never |
| 07 Catalog Assembly | Yes | Never |

**Examples:**
- NocNoc (cross-border sourcing) → `run_skills: ["01", "02", "03", "06", "07"]`
- Rappi (quick commerce sourcing) → `run_skills: ["01", "02", "03", "04", "06", "07"]` — SKU mapping included because Rappi needs the generic format defined for sourcing; sentiment skipped
- Meli (private label + dashboard) → `run_skills: ["01", "02", "03", "04", "05", "06", "07"]` — all skills

**Rule:** When in doubt, include a skill. Skipping is an optimization, not a default.

### Step 6 — Output the structured profile

```json
{
  "platform": "rappi | mercadolibre | [other]",
  "client_name": "string",
  "trend_definition": "1–2 sentences — what counts as a trend for this client",
  "buyer_profile": {
    "description": "who buys, why, behavior mode",
    "motivation": "impulse | aspirational | browsing",
    "delivery_expectation": "minutes | days | flexible"
  },
  "markets": ["MX", "BR"],
  "categories": ["list"],
  "price_bracket": "budget | mid-market | premium",
  "output_mode": "catalog | dashboard",
  "benchmark_sources": ["TikTok US", "Xiaohongshu", "美团闪购"],
  "use_case": "sourcing | private_label | white_label",
  "moq": 50,
  "min_products": 5,
  "max_products": 10,
  "ship_to": "string",
  "run_skills": ["01", "02", "03", "04", "05", "06", "07"]
}
```

After the JSON, include a short **Inference Notes** section listing:
- Which fields were explicitly stated in the brief
- Which were inferred (and from what)
- Any fields left at default and why

---

## Example

**Raw brief (Rappi):**
> "Rappi — recommendation, no specific item. Focus on quick commerce retail, ops items, merchant ops. High margin items: beauty, electronics, toys, sports (generic, non-brand, ~50pcs MOQ), supplements, unique brands like pink coconut water concepts. Also warehouse items: plastic delivery bags, restaurant packaging, aluminium can machine. Ship to Mexico City. Benchmark: 美团闪购 + Taobao Flash."

**Output:**
```json
{
  "platform": "rappi",
  "client_name": "Rappi",
  "trend_definition": "Products currently trending in Chinese quick commerce (美团闪购, Taobao Flash) or US quick commerce not yet widely available in LatAM. Also includes functional operational items (packaging, warehouse supplies) that improve merchant or delivery operations. Generic, non-brand dependent.",
  "buyer_profile": {
    "description": "Urban LatAM consumer on Rappi, impulse or need-based purchases for delivery within 30–60 minutes. Also includes Rappi merchants needing operational supplies.",
    "motivation": "impulse",
    "delivery_expectation": "minutes"
  },
  "markets": ["MX"],
  "categories": ["beauty", "electronics", "toys", "sports", "supplements", "unique_brands", "warehouse_ops", "restaurant_packaging"],
  "price_bracket": "mid-market",
  "output_mode": "catalog",
  "benchmark_sources": ["美团闪购", "Taobao Flash", "TikTok US"],
  "use_case": "sourcing",
  "moq": 50,
  "min_products": 5,
  "max_products": 10,
  "ship_to": "Mexico City",
  "run_skills": ["01", "02", "03", "04", "06", "07"]
}
```

**Inference Notes:**
- `platform`, `categories`, `moq`, `ship_to`, `benchmark_sources`: explicitly stated
- `trend_definition`: composed from benchmark sources + "no specific item" + categories listed
- `output_mode = catalog`: inferred from "recommendation" + "3 catalogs" context
- `price_bracket = mid-market`: inferred from "high margin" + "generic non-brand" + ~50pcs MOQ
- `motivation = impulse`, `delivery_expectation = minutes`: Rappi platform defaults, not contradicted
- `min_products = 5`, `max_products = 10`: default — not specified in brief
- `run_skills`: 05 (Sentiment Analysis) skipped — `use_case = sourcing`, no product design decisions needed

---

## Guardrails

- **Never guess a required field.** If `markets` is not stated and cannot be inferred, ask. A wrong market routes the entire pipeline incorrectly.
- **trend_definition must be specific.** Generic definitions like "products that are popular" are not acceptable. If the brief doesn't give enough to write a specific definition, ask.
- **New platform (not Rappi or Meli):** If the client is neither, still produce the full profile using whatever the brief provides. Do not refuse — just skip the default-inference step and derive everything from the text.
- **Contradictions in the brief:** If the raw brief contains conflicting signals (e.g., "budget products" but also "premium private label"), flag the contradiction and ask before resolving it.
- **Output JSON must be valid.** All downstream skills parse this object directly.

---

## How the Profile Is Used Downstream

| Field | Used by skill(s) |
|---|---|
| `trend_definition` | 01 Data Extraction, 02 Trend Discovery, 03 Trend Synthesis |
| `buyer_profile.motivation` | 03 Trend Synthesis (client filter), 07 Catalog Assembly |
| `benchmark_sources` | 01 Data Extraction (lane priority / benchmark scope) |
| `markets` | 01 Data Extraction, 06 Demand Tier (SerpAPI geo) |
| `categories` | 01 Data Extraction, 04 SKU Mapping |
| `price_bracket` | 06 Demand Tier Classification (margin floor) |
| `output_mode` | 07 Catalog Assembly (format) |
| `use_case` | 04 SKU Mapping (differentiation angle) |
| `moq` | 04 SKU Mapping (sourcing constraint) |
| `min_products` / `max_products` | 03 Trend Synthesis (output count), 07 Catalog Assembly |
| `ship_to` | 07 Catalog Assembly (ops note) |
