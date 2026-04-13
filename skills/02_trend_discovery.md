# Skill: Trend Discovery (Per Lane)

## Classification
**Type:** Skill (LLM reasoning)
**Called:** 3-4 times in parallel, once per lane, after extraction
**Lanes:** `tiktok` | `instagram` | `amazon` | `xiaohongshu`

---

## Role
Given the normalized evidence pack from one source, identify product signals that match the client's trend definition. Each lane is analyzed independently. Do not synthesize across lanes here — that happens in skill 03.

---

## Inputs

| Input | Source | Notes |
|---|---|---|
| `lane_evidence_pack` | Skill 01 | Normalized lane evidence produced by the extraction skill |
| `lane` | Orchestrator | tiktok \| instagram \| amazon \| xiaohongshu |
| `client_profile` | Skill 00 | See `00_client_profile.md` |

---

## Reasoning Process

### Step 1 — Review the extracted evidence pack
Start from the normalized candidates in `lane_evidence_pack`, not from source-native connector output.
For each candidate:
- What product format is actually being referenced?
- What problem does it solve or desire does it fulfill?
- Is the evidence original or mostly reposted / derivative?
- Is the evidence volume strong enough to reason about?

### Step 2 — Apply client's trend definition
Using `client_profile.trend_definition`, decide: does this signal qualify as a trend for this client?
- Rappi: is it quick-commerce deliverable? impulse-purchase fit? or operational utility?
- Meli: is it fashion/aspirational? private-label translatable? searchable on ML?
- If signal doesn't match client definition → discard, do not pass to synthesis

### Step 3 — Assign trend status
For each qualifying signal:
- `OPEN`: Strong engagement/volume in source market (US/China) + low LatAM presence expected
- `CLOSING`: Signal peaked 3–6 months ago, engagement declining
- `CLOSED`: Already well-established in LatAM market (high ML saturation known or expected)

### Step 4 — Assess signal quality
- TikTok/IG original content > reposts (reposts are lagging signals)
- Amazon: rising rank + low review count = early-mover signal
- Xiaohongshu: lifestyle/aesthetic posts with high saves = early fashion signal
- Flag low-quality signals (e.g., single viral post with no follow-through) as LOW strength

### Step 5 — Output per signal

```json
{
  "product_name": "string",
  "lane": "tiktok",
  "trend_status": "OPEN | CLOSING | CLOSED",
  "signal_strength": "HIGH | MEDIUM | LOW",
  "evidence_summary": "1–2 sentence description of what was observed",
  "engagement_data": { "views": N, "engagement_rate": "X%", "recency": "date" },
  "client_fit_note": "why this matches or partially matches the client's trend definition"
}
```

---

## Guardrails

- **Do not mix lanes.** Synthesis is skill 03's job. Report what you see in this lane only.
- **Do not redo extraction work.** If parsing quality looks weak, flag it and reason from the evidence pack you were given.
- **Instagram signals that are clearly TikTok reposts:** Note it, do not count as an independent signal. Tag `repost_of_tiktok: true`.
- **TikTok is primary.** If TikTok and Amazon conflict (TikTok hype, Amazon declining), flag the conflict in `evidence_summary` — do not resolve it here.
- **Do not invent engagement data.** If metrics are unavailable in the evidence pack, mark field as `null` and note it.
- **Minimum evidence bar:** At least 3 independent posts/listings showing the same product signal before classifying as a trend. Single viral posts = LOW strength only.

---

## Data Source Routing

| Lane | Primary Tool | What to Fetch |
|---|---|---|
| `tiktok` | Apify TikTok connector | Search by keyword → posts from last 90 days, sorted by views |
| `instagram` | Apify Instagram connector | Search by hashtag → posts from last 90 days |
| `amazon` | Oxylab amazon.com/s?k=KEYWORD | Top 50 organic results — title, rank, review count, date first available |
| `xiaohongshu` | Apify RED connector | Search by keyword → posts sorted by saves (Meli only) |
