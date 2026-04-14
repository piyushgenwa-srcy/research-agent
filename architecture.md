# Research Agent Architecture

This diagram shows the system in agent/harness terms rather than as a rigid pipeline.

- The **Research Agent** is the central reasoner pursuing the user's goal.
- The **Agentic Harness** steers the agent with prompts, skills, and validators.
- **Tools / Connectors** provide external evidence.
- **Working Artifacts** are structured objects the agent can create, refine, and revisit.

## Agent Architecture

```mermaid
flowchart TB
    U["PM goal / brief / URLs"] --> A["Research Agent"]

    subgraph H["Agentic Harness"]
        P["System prompt / task framing"]
        S["Skills library
        00a market assortment intake
        00 client profiling
        01 extraction guidance
        02 lane trend interpretation
        03 synthesis guidance
        04 SKU concretization
        05 sentiment opportunity analysis
        06 tiering guidance
        07 output assembly"]
        V["Programmatic validators
        required fields
        schema checks
        contradiction checks
        minimum evidence rules"]
    end

    P --> A
    S --> A
    V --> A

    subgraph T["Tools / Connectors"]
        T1["Retailer page fetch / scraper"]
        T2["Apify social connectors"]
        T3["Oxylab marketplace scraping"]
        T4["SerpAPI"]
        T5["TMAPI"]
    end

    A <--> T1
    A <--> T2
    A <--> T3
    A <--> T4
    A <--> T5

    subgraph W["Working Artifacts"]
        W1["market_assortment_context"]
        W2["client_profile"]
        W3["lane_evidence_pack"]
        W4["lane_signal_output"]
        W5["trend_candidates"]
        W6["sku_definitions"]
        W7["sentiment_opportunities"]
        W8["tiered_recommendations"]
    end

    A <--> W1
    A <--> W2
    A <--> W3
    A <--> W4
    A <--> W5
    A <--> W6
    A <--> W7
    A <--> W8

    A --> O["Final outputs
    catalogs / dashboard payloads / recommendation notes"]
```

## Artifact Graph

This second diagram shows common artifact relationships without implying mandatory sequencing.

```mermaid
flowchart LR
    A["PM brief"] --> B["client_profile"]
    C["Retailer URLs / category pages"] --> D["market_assortment_context"]
    D --> B

    B --> E["lane_evidence_pack"]
    D --> E

    E --> F["lane_signal_output"]
    F --> G["trend_candidates"]
    B --> G
    D --> G

    G --> H["sku_definitions"]
    G --> I["sentiment_opportunities"]
    G --> J["tiered_recommendations"]
    H --> J
    I --> J
    D --> J
    B --> J

    J --> K["catalogs / dashboard payloads / recommendation memo"]
    B --> K
    D --> K

    L["Connector results
    social / marketplace / trends / sourcing"] --> E
    L --> G
    L --> J
```

## Notes

- A common run may still resemble a sequence, but the harness is free to skip, revisit, or refine artifacts.
- `00a_market_assortment_intake` is optional and only used when retailer/category inputs materially improve the market view.
- `04_sku_mapping` and `05_sentiment_analysis` are conditional capabilities, not mandatory stages.
