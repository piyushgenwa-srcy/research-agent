# Data Mapping — Research Agent

Reference doc for the orchestrator and for Dan's eng integration. Maps every data source to the skill it feeds, the field it populates, the tool used to fetch it, and current status.

---

## Source → Skill Map

| Data Source | Tool / Connector | Feeds Skill | Field Populated | Client | Status |
|---|---|---|---|---|---|
| TikTok posts + engagement | Apify TikTok connector | 01 Data Extraction (lane: tiktok) | raw_connector_output -> normalized evidence pack | Both | Ivan has connector — share with Dan + Piyush |
| Instagram posts + engagement | Apify Instagram connector | 01 Data Extraction (lane: instagram) | raw_connector_output -> normalized evidence pack | Both | Ivan has connector — share with Dan + Piyush |
| Xiaohongshu (RED) posts + saves | Apify RED connector | 01 Data Extraction (lane: xiaohongshu) | raw_connector_output -> normalized evidence pack | Meli only | Connector status unknown — confirm with Ivan |
| Amazon US organic results | Oxylab → amazon.com/s?k=KEYWORD | 01 Data Extraction (lane: amazon) | raw_connector_output -> normalized evidence pack | Both | Active ✓ |
| TikTok/IG comments + Amazon reviews | Apify connectors | 05 Sentiment Analysis | raw_comments | Meli only | Same connectors as posts — comments endpoint |
| Google Trends (5yr weekly) | SerpAPI | 06 Demand Tier Classification | trend_score (0–100 avg), geo=MX/BR | Both | Active ✓ |
| ML MX listing count | Oxylab → listado.mercadolibre.com.mx/{slug} | 06 Demand Tier Classification | ml_listing_count | Both | Active ✓ — parse "total" from embedded JSON |
| ML BR listing count | Oxylab → lista.mercadolivre.com.br/{slug} | 06 Demand Tier Classification | ml_listing_count (BR) | Meli (BR market) | Active — higher error rate than MX, add retry logic |
| Sourcing price (AliExpress / CJ) | TMAPI | 06 Demand Tier Classification | sourcing_price_usd | Both | Zero balance — needs top-up before use |
| Sourcing price (proxy fallback) | Amazon US retail × 0.30 | 06 Demand Tier Classification | sourcing_price_usd (estimated) | Both | Always available — use when TMAPI unavailable |
| Retail price comp (ML MX) | Oxylab → ML MX product pages | 06 Demand Tier Classification | retail_price_comp_usd | Both | Active ✓ |
| Amazon sales data | Jungle Scout | 06 Demand Tier Classification | Amazon keyword volume, BSR | Both | Key name missing — find in JS Settings → API |
| 美团闪购 / Taobao Flash | Manual research / TMAPI | 03 Trend Synthesis (benchmark) | time_machine reference signal | Rappi only | Manual for now — TMAPI covers Taobao when topped up |

---

## Signal Priority Hierarchy

For trend signals, apply in this order when sources conflict:

1. **TikTok** — primary trend discovery signal
2. **Xiaohongshu** — primary for Meli fashion (Meli only)
3. **Amazon** — validator and early-mover signal (not a trend source itself)
4. **Instagram** — secondary social signal (often lags TikTok; reposts don't count independently)
5. **Google Trends (SerpAPI)** — quantitative validation of trend score, used for tier classification
6. **ML listing count** — saturation validator (not a trend signal — high ML count = trend is old, not new)

---

## Known Gaps

| Gap | Impact | Resolution Path |
|---|---|---|
| No granular LatAM ecommerce sales data (SKU/shop/category/last X days) | Cannot validate actual sales velocity — agent identifies opportunity signals only, not proven sellers | Nubimetrics subscription — not yet active |
| TMAPI zero balance | Sourcing prices fall back to proxy (Amazon × 0.30) — lower confidence margins | Top up TMAPI balance |
| Jungle Scout API key name missing | Amazon keyword volume unavailable | Find key name in JS account Settings → API |
| Xiaohongshu connector status unknown | Meli fashion trend signal incomplete without RED | Confirm with Ivan — he has Apify setup |
| ML BR higher error rate | Brazil saturation data less reliable than MX | Add retry logic with 2 alternate slugs before fallback |
| Partici subscription unclear | US/LatAM trend coverage gap | Confirm subscription status and coverage |

---

## Tool API Reference

| Tool | Base URL / Method | Auth | Docs |
|---|---|---|---|
| SerpAPI (Google Trends) | https://serpapi.com/search | SERP_API_KEY param | serpapi.com/google-trends-api |
| Oxylab (scraper) | https://realtime.oxylabs.io/v1/queries | Basic auth (OXYLAB_USERNAME:OXYLAB_PASSWORD) | oxylabs.io docs |
| TMAPI (AliExpress/Taobao) | http://api.tmapi.top/ | ?apiToken=TMAPI_TOKEN | console.tmapi.io |
| Apify (TikTok/IG/RED) | Apify platform | Ivan's setup — get from Ivan | apify.com |
| Jungle Scout | https://developer.junglescout.com/api/ | "Authorization: KEY_NAME:API_KEY" + X-API-Type: junglescout | Need key name from JS Settings |

All credentials stored in `/Users/piyush-srcy/Documents/cc-proj/research-agent/.env`
