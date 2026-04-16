from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict
from urllib.parse import quote_plus

from .base import basic_auth_header, http_post_json


# Maps ISO market codes to MercadoLibre domain suffixes.
ML_MARKET_DOMAIN: Dict[str, str] = {
    "MX": "com.mx",
    "AR": "com.ar",
    "BR": "com.br",
    "CO": "com.co",
    "CL": "cl",
    "UY": "com.uy",
    "PE": "com.pe",
    "VE": "com.ve",
}


@dataclass
class OxylabsClient:
    username: str
    password: str
    base_url: str = "https://realtime.oxylabs.io/v1/queries"

    def scrape_url(self, url: str, source: str = "universal") -> Dict[str, Any]:
        payload = {"source": source, "url": url, "geo_location": "United States"}
        headers = {"Authorization": basic_auth_header(self.username, self.password)}
        return http_post_json(self.base_url, payload, headers=headers).json()

    def amazon_search(self, query: str, domain: str = "com") -> Dict[str, Any]:
        payload = {
            "source": "amazon_search",
            "domain": domain,
            "query": query,
            "parse": True,
            "start_page": 1,
            "pages": 1,
        }
        headers = {"Authorization": basic_auth_header(self.username, self.password)}
        return http_post_json(self.base_url, payload, headers=headers).json()

    def mercadolibre_search(self, query: str, domain: str = "com.mx") -> Dict[str, Any]:
        """Scrape a MercadoLibre keyword search page via Oxylabs universal scraper.

        Uses the standard MercadoLibre search URL pattern. Oxylabs returns HTML
        content; product extraction is handled by build_mercadolibre_evidence_pack
        in extractors.py.
        """
        url = f"https://www.mercadolibre.{domain}/jm/search?as_word={quote_plus(query)}"
        return self.scrape_url(url, source="universal")
