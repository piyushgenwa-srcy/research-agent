from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from .base import append_query, http_get


@dataclass
class SerpApiClient:
    api_key: str
    base_url: str = "https://serpapi.com/search"

    def google_trends_interest_over_time(self, query: str, geo: str) -> Dict[str, Any]:
        url = append_query(
            self.base_url,
            {
                "engine": "google_trends",
                "data_type": "TIMESERIES",
                "q": query,
                "geo": geo,
                "api_key": self.api_key,
            },
        )
        return http_get(url).json()

    def pinterest_keyword_search(self, keyword: str, market: str = "MX", num: int = 10) -> Dict[str, Any]:
        """Search Google for Pinterest pins matching keyword.

        Uses ``site:pinterest.com`` to surface visual trend signals —
        strong for the 28-45 cohort and early-stage category discovery.
        Returns the raw SerpAPI response including ``organic_results``.
        """
        geo_map = {"MX": "MX", "AR": "AR", "BR": "BR", "CO": "CO", "CL": "CL"}
        gl = geo_map.get(market.upper(), "MX")
        query = f"site:pinterest.com {keyword}"
        url = append_query(
            self.base_url,
            {
                "engine": "google",
                "q": query,
                "gl": gl,
                "hl": "es",
                "num": str(num),
                "api_key": self.api_key,
            },
        )
        return http_get(url).json()

    def instagram_keyword_search(self, keyword: str, market: str = "MX", num: int = 10) -> Dict[str, Any]:
        """Search Google for Instagram posts matching keyword.

        Uses ``site:instagram.com`` to surface real posts with captions as
        snippets.  Returns the raw SerpAPI response including ``organic_results``.
        """
        geo_map = {"MX": "MX", "AR": "AR", "BR": "BR", "CO": "CO", "CL": "CL"}
        gl = geo_map.get(market.upper(), "MX")
        query = f"site:instagram.com {keyword}"
        url = append_query(
            self.base_url,
            {
                "engine": "google",
                "q": query,
                "gl": gl,
                "hl": "es",
                "num": str(num),
                "api_key": self.api_key,
            },
        )
        return http_get(url).json()
